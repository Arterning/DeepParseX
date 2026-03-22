#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from typing import Sequence
from sqlalchemy import Select, select, func, delete, update
from typing import List
from backend.app.admin.service.knowledge_graph.kg_service import kg_service
from backend.app.admin.crud.crud_doc import sys_doc_dao
from backend.app.admin.crud.crud_doc_data import sys_doc_data_dao
from backend.app.admin.crud.crud_doc_chunk import sys_doc_chunk_dao
from backend.app.admin.crud.crud_doc_embedding import sys_doc_embedding_dao
from backend.app.admin.crud.crud_tag import tag_dao
from backend.app.admin.model import SysDoc
from backend.app.admin.model import SubjectPredictObject
from backend.app.admin.model.sys_entity import Entity
from backend.app.admin.model.sys_entity_relationship import EntityRelation
from backend.app.admin.model.sys_entity_type import EntityType
from backend.app.admin.model import SysDocData
from backend.app.admin.model.sys_doc_chunk import SysDocChunk
from backend.app.admin.model.sys_star_doc import sys_star_doc
from backend.app.admin.schema.doc import CreateSysDocParam, UpdateSysDocParam
from backend.common.exception import errors
from backend.database.db_pg import async_db_session
from backend.app.admin.schema.doc_data import CreateSysDocDataParam
from backend.app.admin.schema.doc_chunk import CreateSysDocChunkParam
from backend.app.admin.schema.doc_embdding import CreateSysDocEmbeddingParam
from backend.app.admin.utils.text_processor import embed_text_chunks
from backend.app.admin.service.llm_service import llm_service
from backend.common.log import log
from backend.utils.oss_client import minio_client
from backend.core.conf import settings
import asyncio
import jieba
import json
import duckdb
from collections import defaultdict
import pandas as pd
import pyarrow.parquet as pq
from io import BytesIO
from html.parser import HTMLParser


class HTMLTextExtractor(HTMLParser):
    """HTML 文本提取器"""
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.skip_tags = {'script', 'style', 'head', 'meta', 'link'}
        self.current_tag = None

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag.lower()

    def handle_endtag(self, tag):
        self.current_tag = None

    def handle_data(self, data):
        if self.current_tag not in self.skip_tags:
            text = data.strip()
            if text:
                self.text_parts.append(text)

    def get_text(self):
        return ' '.join(self.text_parts)


def is_html_content(content: str) -> bool:
    """
    检测内容是否为 HTML

    Args:
        content: 要检测的文本内容

    Returns:
        bool: 是否为 HTML 内容
    """
    if not content:
        return False

    # 检查常见的 HTML 标签模式
    html_patterns = [
        r'<!DOCTYPE\s+html',
        r'<html[^>]*>',
        r'<head[^>]*>',
        r'<body[^>]*>',
        r'<div[^>]*>',
        r'<p[^>]*>',
        r'<table[^>]*>',
        r'<span[^>]*>',
        r'<br\s*/?>',
        r'<a\s+href=',
    ]

    content_lower = content[:2000].lower()  # 只检查前2000个字符

    for pattern in html_patterns:
        if re.search(pattern, content_lower, re.IGNORECASE):
            return True

    # 检查是否包含多个 HTML 标签
    tag_count = len(re.findall(r'<[a-zA-Z][^>]*>', content[:2000]))
    return tag_count >= 3


def extract_text_from_html(html_content: str) -> str:
    """
    从 HTML 内容中提取纯文本

    Args:
        html_content: HTML 内容

    Returns:
        str: 提取的纯文本
    """
    if not html_content:
        return ''

    try:
        parser = HTMLTextExtractor()
        parser.feed(html_content)
        text = parser.get_text()

        # 清理多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()

        return text
    except Exception:
        # 如果解析失败，使用正则表达式简单处理
        # 移除 script 和 style 标签及其内容
        text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        # 移除所有 HTML 标签
        text = re.sub(r'<[^>]+>', ' ', text)
        # 清理 HTML 实体
        text = re.sub(r'&nbsp;', ' ', text)
        text = re.sub(r'&[a-zA-Z]+;', ' ', text)
        # 清理多余空白
        text = re.sub(r'\s+', ' ', text)
        return text.strip()




def text_to_tsvector(text: str, mode: str = 'search') -> str:
    """
    将文本转换为 PostgreSQL tsvector 格式字符串，保留原文字符位置

    Args:
        text: 要转换的文本
        mode: 分词模式，'search' 使用 cut_for_search，'accurate' 使用 cut

    Returns:
        tsvector 格式字符串，如 "'北京':3 '天安门':5"

    注意:
        - 位置使用字符位置+1（tsvector 位置从 1 开始）
        - PostgreSQL tsvector 位置最大值为 16383，超过的位置会被截断
        - 单词最大长度为 2046 字节，超过的词会被跳过
    """
    # PostgreSQL tsvector 单词最大长度限制（字节）
    MAX_WORD_BYTES = 2046

    if not text:
        return ''

    # 使用 jieba.tokenize 获取词和位置
    # tokenize 返回: [(word, start, end), ...]
    if mode == 'search':
        tokens = list(jieba.tokenize(text, mode='search'))
    else:
        tokens = list(jieba.tokenize(text, mode='default'))

    if not tokens:
        return ''

    # 收集每个词元的所有位置（同一个词可能出现多次）
    # tsvector 格式: '词元':位置1,位置2
    word_positions = defaultdict(list)

    for word, start, end in tokens:
        # 跳过空白和标点
        word = word.strip()
        if not word or len(word) == 0:
            continue

        # 跳过过长的词（PostgreSQL tsvector 限制）
        if len(word.encode('utf-8')) > MAX_WORD_BYTES:
            continue

        # tsvector 位置从 1 开始，最大 16383
        pos = start + 1
        if pos > 16383:
            pos = 16383

        word_positions[word].append(pos)

    # 生成 tsvector 格式字符串
    # 格式: '词1':1,5,10 '词2':2,8
    tsvector_parts = []
    for word, positions in word_positions.items():
        # 转义单引号，并转换为小写以匹配 plainto_tsquery 的行为
        escaped_word = word.replace("'", "''").lower()
        # 位置去重并排序
        unique_positions = sorted(set(positions))
        pos_str = ','.join(str(p) for p in unique_positions)
        tsvector_parts.append(f"'{escaped_word}':{pos_str}")

    return ' '.join(tsvector_parts)


def text_to_weighted_tsvector(title: str, content: str, doc_type: str = None) -> str:
    """
    将标题和内容转换为带权重的 tsvector 格式字符串

    Args:
        title: 标题文本（权重 A）
        content: 内容文本（权重 B）
        doc_type: 文档类型（权重 A，附加到标题）

    Returns:
        tsvector 格式字符串，带权重，如 "'标题':1A '内容':2B"
    """
    # PostgreSQL tsvector 单词最大长度限制（字节）
    MAX_WORD_BYTES = 2046

    def is_valid_word(word: str) -> bool:
        """检查词是否有效（不为空且长度不超限）"""
        if not word:
            return False
        # 检查 UTF-8 编码后的字节长度
        if len(word.encode('utf-8')) > MAX_WORD_BYTES:
            return False
        return True

    result_parts = []

    # 处理标题（权重 A）
    if title:
        tokens = list(jieba.tokenize(title, mode='search'))
        word_positions = defaultdict(list)

        for word, start, end in tokens:
            word = word.strip()
            if not is_valid_word(word):
                continue
            pos = min(start + 1, 16383)
            word_positions[word].append(pos)

        for word, positions in word_positions.items():
            # 转换为小写以匹配 plainto_tsquery 的行为
            escaped_word = word.replace("'", "''").lower()
            # 添加权重 A
            pos_str = ','.join(f"{p}A" for p in sorted(set(positions)))
            result_parts.append(f"'{escaped_word}':{pos_str}")

    # 处理文档类型（权重 A）
    if doc_type:
        # 转换为小写以匹配 plainto_tsquery 的行为
        escaped_type = doc_type.replace("'", "''").lower()
        # 文档类型放在一个固定位置
        result_parts.append(f"'{escaped_type}':1A")

    # 处理内容（权重 B）
    if content:
        tokens = list(jieba.tokenize(content, mode='search'))
        word_positions = defaultdict(list)

        for word, start, end in tokens:
            word = word.strip()
            if not is_valid_word(word):
                continue
            pos = min(start + 1, 16383)
            word_positions[word].append(pos)

        for word, positions in word_positions.items():
            # 转换为小写以匹配 plainto_tsquery 的行为
            escaped_word = word.replace("'", "''").lower()
            # 添加权重 B
            pos_str = ','.join(f"{p}B" for p in sorted(set(positions)))
            result_parts.append(f"'{escaped_word}':{pos_str}")

    return ' '.join(result_parts)


class SysDocService:

    @staticmethod
    async def compute_embedding(*, id: int):
        doc = await SysDocService.get(pk=id)
        doc_id = doc.id
        doc_name = doc.name
        loop = asyncio.get_running_loop()

        if not doc.content:
            return

        # 处理内容：如果是 HTML 则提取纯文本
        content = doc.content
        if is_html_content(content):
            content = extract_text_from_html(content)

        # 如果提取后内容为空，直接返回
        if not content or not content.strip():
            return

        # 所有文本的向量
        vector_data = await embed_text_chunks(content)
        emb_list=[]
        for vector in vector_data:

            chunk_text = vector['text']

            chunk_embedding = vector['embs']
            # 根据向量维度设置对应的字段
            emb_kwargs = {
                'doc_id': doc_id,
                'doc_name': doc_name,
                'chunk_text': chunk_text,
            }
            
            # 根据向量长度选择对应的字段
            vec_dim = len(chunk_embedding)
            if vec_dim == 384:
                emb_kwargs['embedding_384'] = chunk_embedding
            elif vec_dim == 768:
                emb_kwargs['embedding_768'] = chunk_embedding
            elif vec_dim == 1536:
                emb_kwargs['embedding_1536'] = chunk_embedding
            elif vec_dim == 3072:
                emb_kwargs['embedding_3072'] = chunk_embedding
            else:
                # 默认使用原始的embedding字段
                emb_kwargs['embedding'] = chunk_embedding
            
            emb_obj = CreateSysDocEmbeddingParam(**emb_kwargs)
            emb_list.append(emb_obj)
        # 先删除该文档的旧向量记录，再插入新的
        await SysDocService.delete_doc_embeddings(doc_id=[doc_id])
        await SysDocService.create_doc_bulk_embeddings(emb_list=emb_list)

    @staticmethod
    async def build_graph(pk: int, entity_types: List[str] = None):
        """构建文件的知识图谱
        
        Args:
            pk (int): 文档ID
            entity_types (List[str]): 需要提取的实体类型列表，如['人物', '组织']
            
        Returns:
            list[SubjectPredictObject]: 生成的知识图谱三元组列表
        """
        # 获取文档
        doc = await sys_doc_service.get(pk=pk)
        if not doc.content:
            return []

        # 处理内容：如果是 HTML 则提取纯文本
        content = doc.content
        if is_html_content(content):
            content = extract_text_from_html(content)

        # 如果提取后内容为空，直接返回
        if not content or not content.strip():
            return []

        # 配置知识图谱生成参数
        config = {
            "llm": {
                "max_tokens": 1000,
                "temperature": 0.7
            },
            "max_chunks": 10,
            "chunking": {
                "chunk_size": 10000,
                "overlap": 50
            },
            "standardization": {
                "enabled": False
            },
            "inference": {
                "enabled": False
            },
            "entity_types": entity_types  # 添加实体类型配置
        }

        # 生成知识图谱
        spo_list = await kg_service.generate_knowledge_graph(content, config)
        if not spo_list:
            return []
            
        # 构建SPO对象列表
        spo_objects = []
        # 存储此文档相关的所有实体ID
        doc_entities = set()
        
        from backend.common.context import get_current_user
        _build_user = get_current_user()
        _build_user_id = _build_user.id if _build_user else None

        async with async_db_session.begin() as db:
            entity_cache = {}
            # 导入sys_entity_doc表以用于直接插入记录
            from backend.app.admin.model.sys_entity_doc import sys_entity_doc

            async def get_or_create_entity(
                name: str,
                entity_type: str
            ) -> Entity:
                """获取或创建实体

                Args:
                    name: 实体名称
                    entity_type: 实体类型
                """
                if name in entity_cache:
                    entity = entity_cache[name]
                    # 检查实体是否已经与文档关联
                    if entity.id not in doc_entities:
                        doc_entities.add(entity.id)
                        # 检查数据库中是否已存在该关联
                        existing_relation = await db.execute(
                            select(sys_entity_doc).where(
                                sys_entity_doc.c.entity_id == entity.id,
                                sys_entity_doc.c.doc_id == pk
                            )
                        )
                        if not existing_relation.first():
                            # 向sys_entity_doc表中插入记录，建立实体和文档的关系
                            await db.execute(
                                sys_entity_doc.insert().values(
                                    entity_id=entity.id,
                                    doc_id=pk
                                )
                            )
                            await db.flush()

                    return entity

                # Check if entity exists
                stmt = select(Entity).where(Entity.name == name)
                result = await db.execute(stmt)
                entity = result.scalar_one_or_none()

                if not entity:
                    # Create entity
                    # 设置首次发现来源文档信息
                    entity_to_create = Entity(
                        name=name,
                        entity_type=entity_type,
                        source_doc_id=pk,
                        source_doc_name=doc.name,
                        create_user=_build_user_id,
                    )
                    db.add(entity_to_create)
                    await db.flush()
                    await db.refresh(entity_to_create)
                    entity = entity_to_create

                # 记录实体ID并向sys_entity_doc表中插入记录
                if entity.id not in doc_entities:
                    doc_entities.add(entity.id)
                    # 检查数据库中是否已存在该关联
                    existing_relation = await db.execute(
                        select(sys_entity_doc).where(
                            sys_entity_doc.c.entity_id == entity.id,
                            sys_entity_doc.c.doc_id == pk
                        )
                    )
                    if not existing_relation.first():
                        await db.execute(
                            sys_entity_doc.insert().values(
                                entity_id=entity.id,
                                doc_id=pk
                            )
                        )
                        await db.flush()

                entity_cache[name] = entity
                return entity

            for spo in spo_list:
                # 创建SPO对象
                spo_obj = SubjectPredictObject(
                    subject=spo.get("subject"),
                    subject_type=spo.get("subject_type", "未知"),
                    predicate=spo.get("predicate"),
                    object=spo.get("object"),
                    object_type=spo.get("object_type", "未知"),
                    doc_id=pk
                )
                spo_objects.append(spo_obj)
                db.add(spo_obj)

                subject_name = spo.get("subject")
                subject_type = spo.get("subject_type", "未知")
                object_name = spo.get("object")
                object_type = spo.get("object_type", "未知")
                predicate = spo.get("predicate")

                if not subject_name or not object_name or not predicate:
                    continue

                subject_entity = await get_or_create_entity(subject_name, subject_type)
                object_entity = await get_or_create_entity(object_name, object_type)

                # Create relationship
                if subject_entity and object_entity:
                    stmt = select(EntityRelation).where(
                        EntityRelation.source_id == subject_entity.id,
                        EntityRelation.target_id == object_entity.id,
                        EntityRelation.relation_type == predicate
                    )
                    existing_relation = (await db.execute(stmt)).scalar_one_or_none()

                    if not existing_relation:
                        relation = EntityRelation(
                            source_id=subject_entity.id,
                            target_id=object_entity.id,
                            relation_type=predicate,
                            description=f"{subject_name} -[{predicate}]-> {object_name}"
                        )
                        db.add(relation)
                
        return spo_list

    @staticmethod
    def build_visualize_knowledge_graph(triples: list[SubjectPredictObject]):
        """构建可视化知识图谱
        
        Args:
            triples (list[SubjectPredictObject]): 知识图谱三元组列表
            
        Returns:
            dict: 可视化知识图谱数据
        """
        if not triples:
            print("Warning: No triples provided for visualization")
            return {"nodes": [], "edges": [], "communities": 0}
        
        # Set of all unique nodes
        all_nodes = set()
        
        # Track inferred vs. original relationships
        inferred_edges = set()

        # Node types
        node_types = {}
        
        # Add all subjects and objects as nodes
        for triple in triples:
            subject = triple.subject
            subject_type = triple.subject_type or "未知"
            node_types[subject] = subject_type
            predicate = triple.predicate
            obj = triple.object
            object_type = triple.object_type or "未知"
            node_types[obj] = object_type
            all_nodes.add(subject)
            all_nodes.add(obj)
            
            # Mark inferred relationships
            inferred_edges.add((subject, predicate, obj))

        # Create nodes
        nodes = [{"id": node, "label": node, "type": node_types.get(node, "未知")} for node in all_nodes]

        # Create edges
        edges = [{
            "id": f"{source}-{target}",
            "source": source,
            "target": target,
            "label": predicate,
        } for source, predicate, target in inferred_edges]

        return {
            "nodes": nodes,
            "edges": edges
        }


    @staticmethod
    async def get(*, pk: int) -> SysDoc:
        async with async_db_session() as db:
            sys_doc = await sys_doc_dao.get(db, pk)
            if not sys_doc:
                raise errors.NotFoundError(msg='文件不存在')
            return sys_doc



    @staticmethod
    async def get_select(*, title: str = None, name: str = None, doc_type: list[str] = None,
                          content: str = None, source: str = None, ids: list[int] = None,
                          rangeValue: list[str] = None, current_user_id: int = None,
                          tag_ids: list[int] = None, doc_dir_id: int = None) -> Select:
        if not rangeValue:
            rangeValue = ['', '']
        start_time = rangeValue[0]
        end_time = rangeValue[1]
        return await sys_doc_dao.get_list(
            name=name,
            title=title,
            source=source,
            doc_type=doc_type,
            content=content,
            ids=ids,
            start_time=start_time,
            end_time=end_time,
            current_user_id=current_user_id,
            tag_ids=tag_ids,
            doc_dir_id=doc_dir_id,
        )

    @staticmethod
    def highlight_text(original: str, keywords: List[str], start_tag='<b>', end_tag='</b>') -> str:
        if not original or not keywords:
            return original or ''
        sorted_keywords = sorted(keywords, key=len, reverse=True)
        for kw in sorted_keywords:
            if kw:  # 跳过空关键词
                pattern = re.escape(kw)
                original = re.sub(pattern, lambda m: f'{start_tag}{m.group(0)}{end_tag}', original, flags=re.IGNORECASE)
        return original

    @staticmethod
    def highlight_text_window(
        original: str,
        keywords: List[str],
        start_tag='<b>',
        end_tag='</b>',
        window=30,
        max_snippets=3
    ) -> str:
        # 处理空值情况
        if not original:
            return ''
        if not keywords:
            return original[:200] + ('...' if len(original) > 200 else '')

        # 过滤空关键词并按长度排序
        sorted_keywords = sorted([kw for kw in set(keywords) if kw], key=len, reverse=True)
        if not sorted_keywords:
            return original[:200] + ('...' if len(original) > 200 else '')

        keyword_pattern = '|'.join(map(re.escape, sorted_keywords))

        matches = list(re.finditer(keyword_pattern, original, re.IGNORECASE))
        if not matches:
            return original[:200] + ('...' if len(original) > 200 else '')

        # 合并相邻或重叠的窗口
        merged_windows = []
        current_window = None

        for match in matches:
            start, end = match.start(), match.end()
            window_start = max(start - window, 0)
            window_end = min(end + window, len(original))

            if current_window is None:
                current_window = [window_start, window_end]
            else:
                # 如果当前匹配与上一个窗口重叠或相邻，就合并窗口
                if window_start <= current_window[1]:
                    current_window[1] = max(current_window[1], window_end)
                else:
                    merged_windows.append(tuple(current_window))
                    current_window = [window_start, window_end]

        if current_window:
            merged_windows.append(tuple(current_window))

        # 最多保留 max_snippets 段
        merged_windows = merged_windows[:max_snippets]

        snippets = []
        for start, end in merged_windows:
            snippet = original[start:end]
            # 高亮所有关键词（每段内）
            highlighted = re.sub(keyword_pattern, lambda m: f"{start_tag}{m.group(0)}{end_tag}", snippet, flags=re.IGNORECASE)
            snippets.append(highlighted)

        return " ... ".join(snippets)


    
    @staticmethod
    async def search(*, keyword: str = None, page: int = None, size: int = None):
        """
        在文档分块中搜索关键词

        :param keyword: 搜索关键词
        :param page: 页码
        :param size: 每页大小
        :return: 搜索结果
        """
        if not keyword:
            return {
                "items": [],
                "page": page or 1,
                "size": size or 10,
                "total": 0
            }

        cut = jieba.cut_for_search(keyword)
        seg_list = list(cut)  # 立即转换为列表

        async with async_db_session() as db:
            tokens = ' '.join(seg_list)
            # 使用分块搜索
            res = await sys_doc_chunk_dao.search_chunks(
                db,
                tokens,
                page or 1,
                size or 10,
                search_translation=False
            )

            # 高亮处理
            items = res.get("items")
            for item in items:
                item["doc_title"] = SysDocService.highlight_text(item.get("doc_title"), seg_list)
                chunks = item.get("chunks", [])
                chunk_text = ' '.join([chunk.get("chunk_text") for chunk in chunks])
                item["hit"] = SysDocService.highlight_text_window(chunk_text, seg_list)


            return res

    @staticmethod
    async def similar_search(query: str = None, page: int = None, size: int = None):
        text_emb = await embed_text_chunks(query)
        query_vector = text_emb[0]["embs"]
        res = await SysDocService.search_similar_docs(
            query_vector=query_vector,
            limit=size,
            distance_threshold=1.2
        )
        return res



    @staticmethod
    async def search_similar_docs(
        *,
        query_vector: list[float] = None,
        limit: int = None,
        distance_threshold: float = None,
        doc_id: int = None
    ):
        async with async_db_session() as db:
            res = await sys_doc_embedding_dao.search_chunk_vector(
                db, query_vector, limit, distance_threshold, doc_id
            )
            return res

    @staticmethod
    async def get_all() -> Sequence[SysDoc]:
        async with async_db_session() as db:
            sys_docs = await sys_doc_dao.get_all(db)
            return sys_docs
        
    @staticmethod
    async def get_column_data(column:str)->list:
        async with async_db_session() as db:
            sys_docs = await sys_doc_dao.get_column_data(db,column)
            return sys_docs

    @staticmethod
    async def create(*, obj: CreateSysDocParam) -> SysDoc:
        async with async_db_session.begin() as db:
            doc = await sys_doc_dao.create(db, obj)
            for i in list(doc.tags):
                doc.tags.remove(i)
            tag_list = []
            for tag_name in obj.tags:
                    tag = await tag_dao.get_or_create_by_name(db, tag_name)
                    tag_list.append(tag)
            doc.tags.extend(tag_list)
            return doc


    # 分块大小（字符数）
    CHUNK_SIZE = 5000

    @staticmethod
    async def create_doc_tokens(*, id: int) -> SysDoc:
        """
        为文档创建分块并生成分词向量

        :param id: 文档ID
        :return: 文档对象
        """
        doc = await sys_doc_service.get(pk=id)
        title = doc.title
        content = doc.content
        doc_type = doc.type

        if not content:
            return doc

        # 处理内容：如果是 HTML 则提取纯文本
        if is_html_content(content):
            content = extract_text_from_html(content)

        if not content or not content.strip():
            return doc

        # 先删除该文档的旧分块记录
        async with async_db_session.begin() as db:
            await sys_doc_chunk_dao.delete_by_doc_id(db, [id])

        # 分块处理
        chunks = []
        content_length = len(content)
        chunk_index = 0

        for i in range(0, content_length, SysDocService.CHUNK_SIZE):
            chunk_text = content[i:i + SysDocService.CHUNK_SIZE]

            # 为第一个分块添加标题和文档类型权重
            if chunk_index == 0:
                # 使用 run_in_executor 在线程池中执行分词
                loop = asyncio.get_running_loop()
                chunk_vector_str = await loop.run_in_executor(
                    None, text_to_weighted_tsvector, title, chunk_text, doc_type
                )
            else:
                # 其他分块只索引内容
                loop = asyncio.get_running_loop()
                chunk_vector_str = await loop.run_in_executor(
                    None, text_to_tsvector, chunk_text, 'search'
                )

            # 创建分块对象
            chunk_param = CreateSysDocChunkParam(
                doc_id=id,
                chunk_index=chunk_index,
                chunk_text=chunk_text
            )
            chunks.append((chunk_param, chunk_vector_str))
            chunk_index += 1

        # 批量创建分块并更新向量
        async with async_db_session.begin() as db:
            # 先创建分块记录
            chunk_objects = await sys_doc_chunk_dao.create_bulk(
                db,
                [chunk_param for chunk_param, _ in chunks]
            )

            # 更新每个分块的向量
            for chunk_obj, (_, vector_str) in zip(chunk_objects, chunks):
                await sys_doc_chunk_dao.update_chunk_vector(
                    db,
                    chunk_obj.id,
                    vector_str,
                    is_translation=False
                )

        return doc

    @staticmethod
    async def create_doc_data(*, obj_list: CreateSysDocDataParam) -> SysDocData:
        async with async_db_session.begin() as db:
            return await sys_doc_data_dao.create_bulk(db, obj_list)
    
    @staticmethod
    # 批量插入
    async def create_doc_bulk_embeddings(*, emb_list: list[CreateSysDocEmbeddingParam]) -> list[CreateSysDocEmbeddingParam]:
        async with async_db_session.begin() as db:
            return await sys_doc_embedding_dao.create_bulk(db, emb_list)

    @staticmethod
    async def translate_chunks(*, pk: int, target_language: str) -> list[dict]:
        """
        逐个翻译文档的所有分块

        :param pk: 文档ID
        :param target_language: 目标语言
        :return: 翻译后的分块列表
        """
        async with async_db_session.begin() as db:
            chunks = await sys_doc_chunk_dao.get_by_doc_id(db, pk)
            if not chunks:
                doc = await db.get(SysDoc, pk)
                if doc:
                    doc.translation = "[无内容，跳过翻译]"
                    await db.flush()
                return []

            system_context = f"你是一个专业的翻译助手。请将以下内容翻译成{target_language}。只返回翻译结果，不要添加任何解释。"
            results = []
            for chunk in chunks:
                if not chunk.chunk_text:
                    results.append({
                        'id': chunk.id,
                        'chunk_index': chunk.chunk_index,
                        'chunk_text': chunk.chunk_text,
                        'chunk_translation': chunk.chunk_translation,
                    })
                    continue
                question = (
                    f"请将以下内容翻译成{target_language}：\n"
                    "---\n"
                    f"{chunk.chunk_text}\n"
                    "---\n"
                )
                response = await llm_service.get_llm_response(system_context, question)
                await sys_doc_chunk_dao.update_chunk_translation(db, chunk.id, response)
                results.append({
                    'id': chunk.id,
                    'chunk_index': chunk.chunk_index,
                    'chunk_text': chunk.chunk_text,
                    'chunk_translation': response,
                })

            # 拼接所有翻译后的分块，按 chunk_index 排序
            sorted_results = sorted(results, key=lambda x: x['chunk_index'])
            full_translation = ''.join([
                r['chunk_translation'] or '' for r in sorted_results
            ])

            # 更新文档的 translation 字段
            doc = await db.get(SysDoc, pk)
            if doc:
                doc.translation = full_translation
                await db.flush()

            return results

    @staticmethod
    async def update_chunk(*, chunk_id: int, chunk_text: str | None = None, chunk_translation: str | None = None, user_id: int | None = None, username: str | None = None) -> dict:
        """
        更新分块的文本或翻译内容

        :param chunk_id: 分块ID
        :param chunk_text: 原文内容
        :param chunk_translation: 翻译内容
        :param user_id: 当前用户ID
        :param username: 当前用户名
        :return: 更新后的分块信息
        """
        async with async_db_session.begin() as db:
            chunk = await db.get(SysDocChunk, chunk_id)
            if not chunk:
                raise errors.NotFoundError(msg='分块不存在')

            # 记录是否更新了原文或翻译
            text_updated = chunk_text is not None
            translation_updated = chunk_translation is not None

            if chunk_text is not None:
                chunk.chunk_text = chunk_text
            if chunk_translation is not None:
                chunk.chunk_translation = chunk_translation

            # 更新所属文档的修改人信息和完整内容
            if chunk.doc_id:
                doc = await db.get(SysDoc, chunk.doc_id)
                if doc:
                    doc.updated_by = user_id
                    doc.updated_user = username

                    # 重新获取该文档的所有分块并拼接
                    all_chunks = await sys_doc_chunk_dao.get_by_doc_id(db, chunk.doc_id)
                    sorted_chunks = sorted(all_chunks, key=lambda c: c.chunk_index)

                    # 如果更新了原文，重新拼接 content
                    if text_updated:
                        full_content = ''.join([
                            c.chunk_text or '' for c in sorted_chunks
                        ])
                        doc.content = full_content

                    # 如果更新了翻译，重新拼接 translation
                    if translation_updated:
                        full_translation = ''.join([
                            c.chunk_translation or '' for c in sorted_chunks
                        ])
                        doc.translation = full_translation

            await db.flush()
            return {
                'id': chunk.id,
                'chunk_index': chunk.chunk_index,
                'chunk_text': chunk.chunk_text,
                'chunk_translation': chunk.chunk_translation,
            }

    @staticmethod
    async def base_update(pk: int, obj: dict) -> int:
        async with async_db_session.begin() as db:
            count = await sys_doc_dao.base_update(db, pk, obj)
            return count

    @staticmethod
    async def update(*, pk: int, obj: UpdateSysDocParam) -> int:
        from backend.common.context import get_current_user
        from backend.database.db_pg import user_scoped_db_session
        current_user = get_current_user()
        async with user_scoped_db_session(
            user_id=current_user.id if current_user else None,
            is_superuser=current_user.is_superuser if current_user else True,
        ) as db:
            if current_user and not current_user.is_superuser:
                owned = await sys_doc_dao.check_owned(db, pk, current_user.id)
                if not owned:
                    raise errors.ForbiddenError(msg="无权限修改此文件")
            count = await sys_doc_dao.update(db, pk, obj)
            doc = await sys_doc_dao.get(db, pk)
            for i in list(doc.tags):
                doc.tags.remove(i)
            tag_list = []
            for tag_name in obj.tags:
                    tag = await tag_dao.get_or_create_by_name(db, tag_name)
                    tag_list.append(tag)
            doc.tags.extend(tag_list)
            return count


    @staticmethod
    async def delete(*, pk: list[int]) -> int:
        from backend.common.context import get_current_user
        from backend.database.db_pg import user_scoped_db_session
        current_user = get_current_user()
        async with user_scoped_db_session(
            user_id=current_user.id if current_user else None,
            is_superuser=current_user.is_superuser if current_user else True,
        ) as db:
            if current_user and not current_user.is_superuser:
                count = await sys_doc_dao.delete_owned(db, pk, owner_id=current_user.id)
            else:
                count = await sys_doc_dao.delete(db, pk)
            return count

    @staticmethod
    async def delete_doc_data(*, doc_id: list[int]) -> int:
        async with async_db_session.begin() as db:
            count = await sys_doc_data_dao.delete(db, doc_id)
            return count

    @staticmethod
    async def delete_doc_chunks(*, doc_id: list[int]) -> int:
        async with async_db_session.begin() as db:
            count = await sys_doc_chunk_dao.delete_by_doc_id(db, doc_id)
            return count

    @staticmethod
    async def delete_doc_embeddings(*, doc_id: list[int]) -> int:
        async with async_db_session.begin() as db:
            count = await sys_doc_embedding_dao.delete(db, doc_id)
            return count

    @staticmethod
    async def get_children(pk: int) -> Sequence[SysDoc]:
        async with async_db_session() as db:
            return await sys_doc_dao.get_children(db, pk)

    @staticmethod
    async def get_hot_docs(user_id: int = None) -> Sequence[SysDoc]:
        async with async_db_session() as db:
            docs = await sys_doc_dao.get_hot_docs(db, user_id=user_id)
            return docs


    @staticmethod
    async def collect_doc(user_id: int, collecton_id: int, doc_id: int) -> None:
        async with async_db_session.begin() as db:
            # from sqlalchemy import delete
            # Check if already collected by the user in the specified collection
            if collecton_id is None:
                # If no collection ID is provided, check if the user has collected this doc
                query = select(sys_star_doc).where(
                    sys_star_doc.c.created_by == user_id,
                    sys_star_doc.c.doc_id == doc_id
                )
            else:
                # If a collection ID is provided, check if the user has collected this doc in that collection
                query = select(sys_star_doc).where(
                    sys_star_doc.c.created_by == user_id,
                    sys_star_doc.c.star_id == collecton_id,
                    sys_star_doc.c.doc_id == doc_id
                )
            existing = await db.execute(query)
            if existing.first():
                # Un-collect
                if collecton_id:
                    delete_stmt = delete(sys_star_doc).where(
                        sys_star_doc.c.created_by == user_id,
                        sys_star_doc.c.star_id == collecton_id,
                        sys_star_doc.c.doc_id == doc_id
                    )
                    await db.execute(delete_stmt)
                else:
                    # If no collection ID is provided, delete all stars for this user and doc
                    delete_stmt = delete(sys_star_doc).where(
                        sys_star_doc.c.created_by == user_id,
                        sys_star_doc.c.doc_id == doc_id
                    )
                    await db.execute(delete_stmt)
            else:
                # Collect
                insert_stmt = sys_star_doc.insert().values(
                    star_id=collecton_id, 
                    doc_id=doc_id, 
                    created_by=user_id
                )
                await db.execute(insert_stmt)


    @staticmethod
    async def get_collected_doc_ids(user_id: int, doc_ids: list[int]) -> set[int]:
        if not doc_ids:
            return set()
        async with async_db_session() as db:
            query = select(sys_star_doc.c.doc_id).where(
                sys_star_doc.c.created_by == user_id,
                sys_star_doc.c.doc_id.in_(doc_ids)
            )
            result = await db.execute(query)
            return set(result.scalars().all())

    @staticmethod
    async def get_doc_starred_ids(doc_id: int, user_id: int) -> list[int]:
        """
        获取文档所在的所有收藏夹 ID

        :param doc_id: 文档ID
        :param user_id: 用户ID
        :return: 收藏夹 ID 列表
        """
        async with async_db_session() as db:
            query = select(sys_star_doc.c.star_id).where(
                sys_star_doc.c.doc_id == doc_id,
                sys_star_doc.c.created_by == user_id
            )
            result = await db.execute(query)
            return list(result.scalars().all())


    @staticmethod
    async def get_count(user_id: int | None = None, is_superuser: bool = False):
        """
        获取文档统计数量

        :param user_id: 用户ID
        :param is_superuser: 是否为超级管理员，管理员可查看所有文档
        :return: 包含总数和按类型分组的字典
        """
        async with async_db_session() as db:
            # 管理员查看所有，普通用户只查看自己的
            query_user_id = None if is_superuser else user_id
            res = await sys_doc_dao.get_count(db, user_id=query_user_id)
            return res

    @staticmethod
    async def analyze_data_with_ai(*, pk: int, question: str):
        """使用AI分析文件数据
        
        Args:
            pk (int): 文档ID
            question (str): 用户问题
            
        Returns:
            dict: 包含分析结果的字典
        """
        # 获取文档信息
        doc = await sys_doc_service.get(pk=pk)
        
        # 检查文件类型是否支持数据分析
        if not (doc.file_suffix in ['.parquet', '.csv', '.xlsx', '.xls']):
            return {
                "error": "文件类型不支持数据分析，仅支持 parquet、csv、xlsx、xls 文件"
            }
        
        try:
            # 从 MinIO 获取文件
            bucket_name = settings.BUCKET_NAME
            # 检查bucket是否存在，如果不存在则创建并设置为public权限
            if not minio_client.bucket_exists(bucket_name):
                minio_client.make_bucket(bucket_name)
                # 设置bucket为public权限
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": ["s3:GetObject"],
                            "Effect": "Allow",
                            "Principal": {"AWS": ["*"]},
                            "Resource": [f"arn:aws:s3:::{bucket_name}/*"],
                            "Sid": "PublicRead"
                        }
                    ]
                }
                minio_client.set_bucket_policy(bucket_name, json.dumps(policy))
                log.info(f"Bucket {bucket_name} created successfully with public access policy")
            response = minio_client.get_object(bucket_name, doc.file)
            file_bytes = response.read()
            
            # 根据文件类型加载数据到 pandas DataFrame
            df = None
            if doc.file_suffix == '.parquet':
                buffer = BytesIO(file_bytes)
                table = pq.read_table(buffer)
                df = table.to_pandas()
            elif doc.file_suffix == '.csv':
                df = pd.read_csv(BytesIO(file_bytes))
            elif doc.file_suffix in ['.xlsx', '.xls']:
                engine = "openpyxl" if doc.file_suffix == '.xlsx' else "xlrd"
                df = pd.read_excel(BytesIO(file_bytes), engine=engine)
            
            if df is None or df.empty:
                return {
                    "error": "无法读取文件数据或文件为空"
                }
            
            # 生成数据概要信息
            data_info = {
                "行数": len(df),
                "列数": len(df.columns),
                "列名": list(df.columns),
                "数据类型": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "前5行数据": df.head().to_dict('records')
            }
            
            # 构建 AI 提示词
            system_context = f"""你是一个数据分析专家。用户上传了一个名为"{doc.title}"的数据文件，包含以下信息：

数据概要：
- 行数：{data_info['行数']}
- 列数：{data_info['列数']}
- 列名：{', '.join(data_info['列名'])}
- 数据类型：{data_info['数据类型']}

前5行数据示例：
{pd.DataFrame(data_info['前5行数据']).to_string()}

请根据用户的问题生成相应的SQL查询语句。注意：
1. 表名固定为 'data_table'
2. 只返回SQL语句，不要包含其他解释
3. SQL语句必须是DuckDB兼容的
4. 确保SQL语句是安全的，不包含删除、更新等操作
5. 如果问题不适合用SQL解决，请返回一个查询所有数据的SELECT语句"""

            user_input = f"用户问题：{question}"
            
            # 调用AI生成SQL
            sql_query = await llm_service.get_llm_response(system_context, user_input)
            
            if not sql_query:
                return {
                    "error": "AI生成SQL失败"
                }
            
            # 清理SQL语句
            sql_query = sql_query.strip()
            if sql_query.startswith('```sql'):
                sql_query = sql_query[6:]
            if sql_query.endswith('```'):
                sql_query = sql_query[:-3]
            sql_query = sql_query.strip()
            
            # 使用DuckDB执行SQL查询
            conn = duckdb.connect(':memory:')
            
            # 将DataFrame注册为表
            conn.register('data_table', df)
            
            # 执行SQL查询
            result = conn.execute(sql_query).fetchdf()
            
            # 关闭连接
            conn.close()
            
            # 返回结果
            return {
                "question": question,
                "sql_query": sql_query,
                "data_info": data_info,
                "result": {
                    "columns": list(result.columns),
                    "data": result.to_dict('records'),
                    "row_count": len(result)
                }
            }
            
        except Exception as e:
            print(f"数据分析出错: {str(e)}")
            return {
                "error": f"数据分析出错: {str(e)}"
            }

    @staticmethod
    async def extract_entities_by_types(pk: int, type_definitions: List[dict]):
        """根据实体类型定义提取实体

        Args:
            pk (int): 文档ID
            type_definitions (List[dict]): 类型定义列表
                格式: [{"type_name": "人物", "fields": ["性别", "国籍"], "description": ""}]

        Returns:
            int: 提取到的实体数量
        """
        from backend.app.admin.model.sys_entity_doc import sys_entity_doc
        import json

        # 获取文档
        doc = await sys_doc_service.get(pk=pk)
        if not doc.content:
            raise errors.ForbiddenError(msg='文档内容为空')

        # 处理内容：如果是 HTML 则提取纯文本
        content = doc.content
        if is_html_content(content):
            content = extract_text_from_html(content)

        # 如果提取后内容为空，返回错误
        if not content or not content.strip():
            raise errors.ForbiddenError(msg='文档内容为空')

        # 限制内容长度（避免 token 超限）
        max_content_length = 8000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."

        from backend.common.context import get_current_user
        _extract_user = get_current_user()
        _extract_user_id = _extract_user.id if _extract_user else None

        async with async_db_session.begin() as db:
            system_prompt = f"""你是一个专业的实体提取助手。请从给定的文本中提取实体信息。

实体类型定义：
{json.dumps(type_definitions, ensure_ascii=False, indent=2)}

【核心原则】只提取专有名词，即在现实世界中有唯一对应具体对象的命名实体。

禁止提取的内容（重要）：
- 泛称/类别词：如"企业"、"公司"、"政府"、"机构"、"部门"、"单位"、"组织"、"团体"、"机关"、"当局"、"行业"等，即使上下文指代某类组织，也不能作为实体
- 抽象角色或身份：如"负责人"、"官员"、"专家"、"领导"、"工作人员"、"相关人员"等，必须有具体姓名才能提取
- 不完整的描述：如"某公司"、"该机构"、"相关部门"、"有关方面"等代词或模糊指代
- 纯数值、日期、金额、度量值

有效实体示例：
- 人物："张伟"、"Elon Musk"（有具体姓名）→ 有效；"负责人"、"发言人" → 无效
- 组织："腾讯科技有限公司"、"清华大学"、"国家发展改革委" → 有效；"企业"、"政府"、"公司" → 无效
- 判断标准：能否在现实中找到唯一对应的具体实体？能则提取，否则跳过。

请严格按照以下JSON格式返回提取结果：
{{
  "entities": [
    {{
      "type": "实体类型名称",
      "name": "实体名称",
      "description": "实体描述（可选）",
      "properties": {{
        "字段名1": "值1",
        "字段名2": "值2"
      }}
    }}
  ]
}}

注意事项：
1. 只提取明确出现在文本中的实体
2. properties 中的字段必须严格按照实体类型定义的 fields 来提取
3. 如果某个字段在文本中没有找到对应信息，则不要包含该字段
4. 确保返回的是合法的JSON格式
5. name 字段是必填的，description 可选
6. 宁可少提取，也不要提取泛称或抽象概念
"""

            user_prompt = f"请从以下文本中提取实体：\n\n{content}"

            # 调用 AI
            try:
                response = await llm_service.get_llm_response(system_prompt, user_prompt)

                # 解析 AI 返回的结果
                # 尝试提取 JSON（可能被包裹在 markdown 代码块中）
                response_text = response.strip()
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                elif "```" in response_text:
                    json_start = response_text.find("```") + 3
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()

                result = json.loads(response_text)
                entities_data = result.get("entities", [])

                if not entities_data:
                    return 0

                # 保存实体到数据库
                entity_count = 0
                for entity_data in entities_data:
                    entity_type_name = entity_data.get("type")
                    entity_name = entity_data.get("name")
                    entity_description = entity_data.get("description")
                    entity_properties = entity_data.get("properties", {})

                    if not entity_name or not entity_type_name:
                        continue

                    # 检查是否已存在同名实体
                    existing_entities = await db.execute(
                        select(Entity).where(
                            Entity.name == entity_name,
                            Entity.entity_type == entity_type_name
                        )
                    )
                    existing_entity = existing_entities.scalars().first()

                    if existing_entity:
                        # 更新已存在的实体（合并属性）
                        if existing_entity.properties:
                            existing_entity.properties.update(entity_properties)
                        else:
                            existing_entity.properties = entity_properties

                        if entity_description and not existing_entity.description:
                            existing_entity.description = entity_description

                        entity_id = existing_entity.id
                    else:
                        # 创建新实体
                        new_entity = Entity(
                            name=entity_name,
                            description=entity_description,
                            entity_type=entity_type_name,
                            entity_type_id=None,
                            properties=entity_properties,
                            source_doc_id=pk,
                            source_doc_name=doc.name or doc.title,
                            create_user=_extract_user_id,
                        )
                        db.add(new_entity)
                        await db.flush()
                        entity_id = new_entity.id
                        entity_count += 1

                    # 关联实体和文档
                    existing_relation = await db.execute(
                        select(sys_entity_doc).where(
                            sys_entity_doc.c.entity_id == entity_id,
                            sys_entity_doc.c.doc_id == pk
                        )
                    )
                    if not existing_relation.first():
                        await db.execute(
                            sys_entity_doc.insert().values(
                                entity_id=entity_id,
                                doc_id=pk
                            )
                        )

                # 标记文档已提取实体
                await db.execute(update(SysDoc).where(SysDoc.id == pk).values(entity_extracted=1))
                await db.commit()
                return entity_count

            except json.JSONDecodeError as e:
                raise errors.ServerError(msg=f"AI 返回的结果格式错误: {str(e)}")
            except Exception as e:
                raise errors.ServerError(msg=f"提取实体失败: {str(e)}")

    @staticmethod
    async def generate_summary(id: int):
        """生成文档摘要

        Args:
            id (int): 文档ID

        Returns:
            str: 生成的摘要
        """
        # 提示词模板
        SYSTEM_CONTEXT_TEMPLATE = "你是一个专业的文档摘要生成器。请根据以下{content_type}生成一个{summary_type}的中文摘要。必须使用中文回答，不允许使用其他语言。"
        QUESTION_TEMPLATE = (
            "请根据以下{content_type}生成一个{summary_type}的中文摘要：\n"
            "---\n"
            "{content}\n"
            "---\n"
            "{instruction}\n"
            "请务必使用中文回答。"
        )

        # 获取文档
        doc = await sys_doc_service.get(pk=id)
        if not doc.content:
            return ""

        # 处理内容：如果是 HTML 则提取纯文本
        content = doc.content
        if is_html_content(content):
            content = extract_text_from_html(content)

        # 如果提取后内容为空，直接返回
        if not content or not content.strip():
            return ""

        # 字符限制阈值
        CONTENT_LENGTH_THRESHOLD = 5000

        # 检查文档内容长度
        if len(content) <= CONTENT_LENGTH_THRESHOLD:
            # 内容未超限，直接生成摘要
            system_context = SYSTEM_CONTEXT_TEMPLATE.format(
                content_type="文件内容",
                summary_type="简洁"
            )
            question = QUESTION_TEMPLATE.format(
                content_type="文件内容",
                summary_type="简洁",
                content=content,
                instruction="作为一个人工智能助手，你的回答要尽可能严谨。"
            )
        else:
            # 内容超限，使用向量检索方式
            # 固定查询词
            summary_query = "请总结这个文档的核心内容、主要观点和关键信息"

            # 对查询词进行向量化
            question_text_emb = await embed_text_chunks(summary_query)
            query_vector = question_text_emb[0]["embs"]

            # 检索该文档的相关片段（限定doc_id）
            similar_docs = await sys_doc_service.search_similar_docs(
                query_vector=query_vector,
                limit=10,
                distance_threshold=1.2,
                doc_id=id
            )

            # 构建上下文
            context_list = []
            for idx, doc_chunk in enumerate(similar_docs):
                if doc_chunk.chunk_text:
                    context_list.append(f"片段{idx + 1}: {doc_chunk.chunk_text}")

            context = "\n\n".join(context_list)

            # 构建系统提示词
            if context:
                system_context = SYSTEM_CONTEXT_TEMPLATE.format(
                    content_type="文档片段",
                    summary_type="简洁、全面"
                )
                question = QUESTION_TEMPLATE.format(
                    content_type="文档片段",
                    summary_type="简洁、全面",
                    content=context,
                    instruction="作为一个人工智能助手，你的回答要尽可能严谨、准确，并综合所有片段的关键信息。"
                )
            else:
                # 如果没有检索到相关片段，使用文档的前N个字符
                system_context = SYSTEM_CONTEXT_TEMPLATE.format(
                    content_type="文件内容",
                    summary_type="简洁"
                )
                question = QUESTION_TEMPLATE.format(
                    content_type="文件内容",
                    summary_type="简洁",
                    content=content[:CONTENT_LENGTH_THRESHOLD],
                    instruction="作为一个人工智能助手，你的回答要尽可能严谨。"
                )

        response = await llm_service.get_llm_response(system_context, question)
        await sys_doc_service.base_update(pk=id, obj={
            'desc': response
        })
        return response


sys_doc_service = SysDocService()