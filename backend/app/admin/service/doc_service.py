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
from backend.app.admin.service.embedding_service import embed_text_chunks
from backend.app.admin.service.llm_service import llm_service
from backend.common.log import log
from backend.utils.oss_client import minio_client
from backend.core.conf import settings
from backend.app.admin.conf import admin_settings
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




def _is_valid_tsvector_word(word: str, max_bytes: int = 2046) -> bool:
    """检查词是否可安全用于 tsvector（无控制字符、无非法 Unicode、长度不超限）"""
    if not word:
        return False
    # 包含控制字符（\x00-\x1f, \x7f）或 Unicode 替换符 \ufffd 的词不合法
    for ch in word:
        if ch == '\ufffd' or (ord(ch) < 0x20 and ch not in ('\t', '\n', '\r')) or ord(ch) == 0x7f:
            return False
    if len(word.encode('utf-8')) > max_bytes:
        return False
    return True


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
        if not _is_valid_tsvector_word(word):
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
    result_parts = []

    # 处理标题（权重 A）
    if title:
        tokens = list(jieba.tokenize(title, mode='search'))
        word_positions = defaultdict(list)

        for word, start, end in tokens:
            word = word.strip()
            if not _is_valid_tsvector_word(word):
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
            if not _is_valid_tsvector_word(word):
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


_QUESTION_RE = re.compile(
    r'(是什么|是啥|怎么|怎样|如何|为什么|为何|有哪些|有什么'
    r'|能否|可以|介绍|解释|说明|分析|总结|比较|区别|原因|\?|？)'
)


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
                          tag_ids: list[int] = None, doc_dir_id: int = None,
                          status: int = None) -> Select:
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
            status=status,
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
        doc_id: int = None,
        doc_ids: list[int] | None = None,
    ):
        async with async_db_session() as db:
            res = await sys_doc_embedding_dao.search_chunk_vector(
                db, query_vector, limit, distance_threshold, doc_id, doc_ids
            )
            return res

    @staticmethod
    async def search_fulltext_chunks(
        *,
        keyword: str,
        limit: int = 10,
        doc_id: int = None,
        doc_ids: list[int] | None = None,
    ):
        """全文检索分块（面向 RAG 混合召回）"""
        async with async_db_session() as db:
            return await sys_doc_chunk_dao.search_chunks_for_rag(
                db, keyword, limit, doc_id, doc_ids
            )

    @staticmethod
    async def batch_move(*, doc_ids: list[int], doc_dir_id: int | None) -> int:
        """批量移动文件到指定目录（一次 SQL 完成）"""
        from sqlalchemy import update as sa_update
        async with async_db_session.begin() as db:
            result = await db.execute(
                sa_update(SysDoc)
                .where(SysDoc.id.in_(doc_ids))
                .values(doc_dir_id=doc_dir_id)
            )
            return result.rowcount

    @staticmethod
    async def ai_search_docs(
        question: str,
        rewritten_query: str,
        limit: int = 500,
        score_ratio_threshold: float = 0.3,
    ) -> list[dict]:
        """AI 混合检索：向量 + 全文 + RRF 融合，按文件去重后返回相关文件。

        score_ratio_threshold: 只保留文件得分 >= 最高分 × 该比例的结果，过滤长尾。
        """
        query_vector = (await embed_text_chunks(rewritten_query))[0]["embs"]

        vector_results, fulltext_results = await asyncio.gather(
            SysDocService.search_similar_docs(
                query_vector=query_vector,
                limit=limit,
                distance_threshold=1.2,
            ),
            SysDocService.search_fulltext_chunks(keyword=rewritten_query, limit=limit),
        )

        # 过滤空 chunk 及极短 chunk（如 "News Alert" 这类无上下文的噪声片段）
        min_chunk_len = 20
        vector_results = [r for r in vector_results if r.chunk_text and len(r.chunk_text.strip()) >= min_chunk_len]
        fulltext_results = [r for r in fulltext_results if r.chunk_text and len(r.chunk_text.strip()) >= min_chunk_len]
        log.debug(f"[ai_search] vector={len(vector_results)} fulltext={len(fulltext_results)}")

        # 使用 (doc_id, chunk_text[:100]) 作为 key，避免不同文件中相同内容的 chunk
        # 共用同一个 key 导致分数跨文件叠加（原 _rrf_fusion 只用 chunk_text[:200] 作 key，
        # 内容相同的垃圾邮件会把分数全部堆到同一个 key 上，虚高到 0.46）。
        k = 60
        chunk_scores: dict[tuple, dict] = {}

        for rank, row in enumerate(vector_results):
            key = (row.doc_id, (row.chunk_text or "")[:100])
            if key not in chunk_scores:
                chunk_scores[key] = {
                    "doc_id": row.doc_id,
                    "doc_name": row.doc_name,
                    "chunk_text": row.chunk_text,
                    "rrf_score": 0.0,
                }
            chunk_scores[key]["rrf_score"] += 1.0 / (k + rank)

        for rank, row in enumerate(fulltext_results):
            key = (row.doc_id, (row.chunk_text or "")[:100])
            if key not in chunk_scores:
                chunk_scores[key] = {
                    "doc_id": row.doc_id,
                    "doc_name": row.doc_name,
                    "chunk_text": row.chunk_text,
                    "rrf_score": 0.0,
                }
            chunk_scores[key]["rrf_score"] += 1.0 / (k + rank)

        # 按文件分组：每文件只取 top-3 chunk 累加，防止长文档因分块数多得分虚高
        _doc_chunk_list: dict[int, list] = {}
        for chunk in chunk_scores.values():
            doc_id = chunk["doc_id"]
            if doc_id is None:
                continue
            if doc_id not in _doc_chunk_list:
                _doc_chunk_list[doc_id] = []
            _doc_chunk_list[doc_id].append(chunk)

        MAX_CHUNKS_PER_DOC = 3
        doc_scores: dict[int, dict] = {}
        for doc_id, chunks in _doc_chunk_list.items():
            top_chunks = sorted(chunks, key=lambda c: c["rrf_score"], reverse=True)[:MAX_CHUNKS_PER_DOC]
            best = top_chunks[0]
            doc_scores[doc_id] = {
                "doc_id": doc_id,
                "rrf_score": sum(c["rrf_score"] for c in top_chunks),
                "best_chunk_score": best["rrf_score"],
                "content_preview": (best["chunk_text"] or ""),
            }

        # 全文命中的 doc_id 集合：只在向量中命中、全文完全没命中的文件降权
        # "News Alert" 类邮件不含关键词，不会出现在全文结果中，降权后被阈值过滤掉
        fulltext_doc_ids = {r.doc_id for r in fulltext_results}
        vector_only_penalty = 0.2
        for doc in doc_scores.values():
            if doc["doc_id"] not in fulltext_doc_ids:
                doc["rrf_score"] *= vector_only_penalty
                doc["best_chunk_score"] *= vector_only_penalty

        sorted_docs = sorted(doc_scores.values(), key=lambda x: x["best_chunk_score"], reverse=True)
        if not sorted_docs:
            return []

        # 只保留分数 >= 最高分 × score_ratio_threshold 的文件，过滤长尾
        max_score = sorted_docs[0]["best_chunk_score"]
        min_score = max_score * score_ratio_threshold
        sorted_docs = [d for d in sorted_docs if d["best_chunk_score"] >= min_score]
        log.debug(f"[ai_search] 过滤后保留 {len(sorted_docs)} 个文件（阈值 {min_score:.6f}）")

        doc_ids = [d["doc_id"] for d in sorted_docs]
        async with async_db_session() as db:
            from sqlalchemy import select as sa_select
            rows = (await db.execute(
                sa_select(SysDoc).where(SysDoc.id.in_(doc_ids))
            )).scalars().all()
        doc_map = {doc.id: doc for doc in rows}

        results = []
        for item in sorted_docs:
            doc = doc_map.get(item["doc_id"])
            if not doc:
                continue
            results.append({
                "id": doc.id,
                "title": doc.title,
                "name": doc.name,
                "type": doc.type,
                "size": doc.size,
                "status": doc.status,
                "desc": doc.desc,
                "created_time": doc.created_time,
                "created_user": doc.created_user,
                "rrf_score": item["rrf_score"],
                "content_preview": item["content_preview"],
            })
        return results

    @staticmethod
    def is_question(text: str) -> bool:
        return bool(_QUESTION_RE.search(text))

    @staticmethod
    async def ai_overview(question: str, search_results: list[dict]) -> dict:
        """基于已有的 ai_search 结果生成 AI 概览回答（无额外向量检索）。"""
        if not SysDocService.is_question(question):
            return {"is_question": False, "answer": None, "references": []}

        top = [r for r in search_results[:10] if r.get("content_preview")]
        if not top:
            return {"is_question": True, "answer": None, "references": []}

        context = "\n\n".join(
            f"[{i + 1}] 《{r.get('title') or r.get('name') or '文件'}》\n{r['content_preview']}"
            for i, r in enumerate(top)
        )
        system_prompt = (
            "你是一个知识库助手。请根据以下参考资料简洁、准确地回答用户问题。"
            "直接给出答案，不要重复问题，不要说根据资料等套话。"
            "如参考资料不足，如实说明。"
        )
        user_prompt = f"参考资料：\n{context}\n\n问题：{question}"
        answer = await llm_service.get_llm_response(system_prompt, user_prompt)

        references = [
            {
                "doc_id": r["id"],
                "doc_name": r.get("title") or r.get("name"),
                "content_preview": (r.get("content_preview") or ""),
            }
            for r in top
        ]
        return {"is_question": True, "answer": answer, "references": references}

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
    CHUNK_OVERLAP = 0

    # 句子边界：中英文标点，lookbehind 保留标点本身
    _SENT_SPLIT_RE = re.compile(r'(?<=[。！？…!?.])\s*')
    # 中文句尾标点（判断段落边界时最可靠）
    _CN_SENT_END_RE = re.compile(r'[。！？…]\s*$')
    # 英文句尾标点
    _EN_SENT_END_RE = re.compile(r'[.!?]\s*$')
    @staticmethod
    def _is_cjk(ch: str) -> bool:
        cp = ord(ch)
        return (
            0x4E00 <= cp <= 0x9FFF   # CJK 统一汉字
            or 0x3400 <= cp <= 0x4DBF  # CJK 扩展 A
            or 0x3000 <= cp <= 0x303F  # CJK 符号与标点（。，！？等）
            or 0xFF00 <= cp <= 0XFFEF  # 全角字符
        )
    # 单行被视为段落边界的最大字符数（标题/短句）
    _SHORT_LINE_THRESH = 20

    @staticmethod
    def _detect_paragraphs(text: str) -> list[str]:
        """将原始文本拆分为段落列表，兼容 \\n\\n 和 OCR 产生的单 \\n 边界。

        判断单个 \\n 是否为段落边界的启发式规则（满足任一即切段）：
        - 当前行以中文句尾标点结尾（。！？…）：最可靠
        - 当前行以英文标点结尾（.!?）且下一行首字符大写/数字
        - 当前行字符数 ≤ SHORT_LINE_THRESH（标题或独立短句）
        否则视为段落内软换行，与下一行合并。
        """
        _cn = SysDocService._CN_SENT_END_RE
        _en = SysDocService._EN_SENT_END_RE
        thresh = SysDocService._SHORT_LINE_THRESH

        def smart_join(parts: list[str]) -> str:
            """中文行之间不加空格，英文行之间加空格。"""
            if not parts:
                return ''
            result = parts[0]
            for part in parts[1:]:
                sep = '' if result and SysDocService._is_cjk(result[-1]) else ' '
                result += sep + part
            return result

        paragraphs: list[str] = []
        buf: list[str] = []

        lines = text.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                # 空行：明确的段落边界
                if buf:
                    paragraphs.append(smart_join(buf))
                    buf = []
                continue

            buf.append(stripped)

            next_stripped = lines[i + 1].strip() if i + 1 < len(lines) else ''
            # 只有下一行非空时才需要判断是否切段（下一行空的话下次循环会自动切）
            if not next_stripped:
                continue

            is_para_break = (
                len(stripped) <= thresh                                    # 短行/标题
                or (_en.search(stripped) and (                            # 英文句尾
                    next_stripped[0].isupper() or next_stripped[0].isdigit()
                ))
            )
            if is_para_break:
                paragraphs.append(smart_join(buf))
                buf = []

        if buf:
            paragraphs.append(smart_join(buf))

        return [p for p in paragraphs if p.strip()]

    @staticmethod
    def _split_into_chunks(text: str, chunk_size: int = 5000, overlap: int = 150) -> list[str]:
        """按段落 → 句子 → 字符三级边界分块，避免在段落/句子中间截断。

        Args:
            text: 待分块纯文本
            chunk_size: 单块最大字符数
            overlap: 相邻块之间从上一块尾部借用的字符数（0 = 不重叠）
        """

        def _split_para_by_sentences(para: str) -> list[str]:
            """将超长段落按句子拆分，句子本身超长则按字符兜底。"""
            sents = [s for s in SysDocService._SENT_SPLIT_RE.split(para) if s.strip()]
            if not sents:
                return [para[i:i + chunk_size] for i in range(0, len(para), chunk_size)]

            result: list[str] = []
            buf: list[str] = []
            buf_len = 0
            for sent in sents:
                if len(sent) >= chunk_size:
                    # 单句超长，先落盘缓冲，再按字符切
                    if buf:
                        result.append(' '.join(buf))
                        buf, buf_len = [], 0
                    result.extend(sent[i:i + chunk_size] for i in range(0, len(sent), chunk_size))
                elif buf_len + len(sent) > chunk_size:
                    result.append(''.join(buf))
                    buf, buf_len = [sent], len(sent)
                else:
                    buf.append(sent)
                    buf_len += len(sent)
            if buf:
                result.append(''.join(buf))
            return result

        if admin_settings.SMART_PARAGRAPH_DETECTION:
            paras = SysDocService._detect_paragraphs(text)
        else:
            paras = [p.strip() for p in text.split('\n\n') if p.strip()]
        if not paras:
            return [text] if text.strip() else []

        chunks: list[str] = []
        buf_parts: list[str] = []
        buf_len = 0

        for para in paras:
            if len(para) > chunk_size:
                # 超长段落：先落盘当前缓冲，再按句子拆分
                if buf_parts:
                    chunks.append('\n\n'.join(buf_parts))
                    buf_parts, buf_len = [], 0
                chunks.extend(_split_para_by_sentences(para))
            elif buf_len and buf_len + len(buf_parts) * 2 + len(para) > chunk_size:
                # 加入当前段落会溢出，先落盘
                chunks.append('\n\n'.join(buf_parts))
                buf_parts, buf_len = [para], len(para)
            else:
                buf_parts.append(para)
                buf_len += len(para)

        if buf_parts:
            chunks.append('\n\n'.join(buf_parts))

        if not chunks:
            return []

        # 尾部重叠：将上一块末尾 overlap 个字符拼接到下一块开头
        if overlap and len(chunks) > 1:
            overlapped = [chunks[0]]
            for i in range(1, len(chunks)):
                tail = overlapped[-1][-overlap:]
                overlapped.append(tail + '\n\n' + chunks[i])
            return overlapped

        return chunks

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

        chunk_texts = SysDocService._split_into_chunks(
            content,
            chunk_size=SysDocService.CHUNK_SIZE,
            overlap=SysDocService.CHUNK_OVERLAP,
        )

        loop = asyncio.get_running_loop()
        chunks = []
        for chunk_index, chunk_text in enumerate(chunk_texts):
            if chunk_index == 0:
                chunk_vector_str = await loop.run_in_executor(
                    None, text_to_weighted_tsvector, title, chunk_text, doc_type
                )
            else:
                chunk_vector_str = await loop.run_in_executor(
                    None, text_to_tsvector, chunk_text, 'search'
                )
            chunk_param = CreateSysDocChunkParam(
                doc_id=id,
                chunk_index=chunk_index,
                chunk_text=chunk_text,
            )
            chunks.append((chunk_param, chunk_vector_str))

        # 批量创建分块并更新向量
        async with async_db_session.begin() as db:
            chunk_objects = await sys_doc_chunk_dao.create_bulk(
                db,
                [chunk_param for chunk_param, _ in chunks]
            )
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
    async def translate_pages(*, pk: int, target_language: str) -> list[dict]:
        """
        逐个翻译文档的 OCR 分页

        :param pk: 文档ID
        :param target_language: 目标语言
        :return: 翻译后的分页列表
        """
        async with async_db_session.begin() as db:
            doc = await db.get(SysDoc, pk)
            if not doc:
                raise errors.NotFoundError(msg='文件不存在')

            pages = doc.ocr_pages
            if not pages:
                doc.ocr_pages_translation = []
                doc.translation = "[无OCR分页，跳过翻译]"
                await db.flush()
                return []

            system_context = f"你是一个专业的翻译助手。请将以下内容翻译成{target_language}。只返回翻译结果，不要添加任何解释。"
            results = []
            for page in pages:
                page_text = (page.get('text') or '').strip()
                page_num = page.get('page', 0)
                if not page_text:
                    results.append({
                        'page': page_num,
                        'text': '',
                        'translation': '',
                    })
                    continue
                question = (
                    f"请将以下内容翻译成{target_language}：\n"
                    "---\n"
                    f"{page_text}\n"
                    "---\n"
                )
                response = await llm_service.get_llm_response(system_context, question)
                results.append({
                    'page': page_num,
                    'text': page_text,
                    'translation': response,
                })

            # 按页码排序
            sorted_results = sorted(results, key=lambda x: x['page'])
            full_translation = ''.join([
                r['translation'] or '' for r in sorted_results
            ])

            # 更新文档的 ocr_pages_translation 和 translation 字段
            doc.ocr_pages_translation = sorted_results
            doc.translation = full_translation
            await db.flush()

            return sorted_results

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
    async def update_ocr_page(*, pk: int, page: int, text: str, user_id: int | None = None, username: str | None = None) -> dict:
        """
        更新 OCR 分页的原文内容

        :param pk: 文档ID
        :param page: 页码（从1开始）
        :param text: 更新后的文本
        :param user_id: 当前用户ID
        :param username: 当前用户名
        :return: 更新后的分页信息
        """
        async with async_db_session.begin() as db:
            doc = await db.get(SysDoc, pk)
            if not doc:
                raise errors.NotFoundError(msg='文件不存在')

            pages = doc.ocr_pages
            if not pages:
                raise errors.NotFoundError(msg='文件没有OCR分页')

            target = None
            for p in pages:
                if p.get('page') == page:
                    target = p
                    break

            if not target:
                raise errors.NotFoundError(msg=f'页码 {page} 不存在')

            target['text'] = text

            # 更新文档的修改人信息
            doc.updated_by = user_id
            doc.updated_user = username

            # 重新拼接 content
            full_content = ''.join([p.get('text') or '' for p in pages])
            doc.content = full_content

            # 清除旧翻译（原文已变更，翻译失效）
            # doc.ocr_pages_translation = None
            # doc.translation = None

            await db.flush()
            return {
                'page': target['page'],
                'text': target['text'],
            }

    @staticmethod
    async def update_ocr_page_translation(*, pk: int, page: int, translation: str, user_id: int | None = None, username: str | None = None) -> dict:
        """
        更新 OCR 分页的翻译内容

        :param pk: 文档ID
        :param page: 页码（从1开始）
        :param translation: 更新后的翻译文本
        :param user_id: 当前用户ID
        :param username: 当前用户名
        :return: 更新后的分页信息
        """
        async with async_db_session.begin() as db:
            doc = await db.get(SysDoc, pk)
            if not doc:
                raise errors.NotFoundError(msg='文件不存在')

            pages = doc.ocr_pages_translation
            if not pages:
                raise errors.NotFoundError(msg='文件没有OCR翻译分页')

            target = None
            for p in pages:
                if p.get('page') == page:
                    target = p
                    break

            if not target:
                raise errors.NotFoundError(msg=f'页码 {page} 不存在')

            target['translation'] = translation

            # 更新文档的修改人信息
            doc.updated_by = user_id
            doc.updated_user = username

            # 重新拼接 translation
            full_translation = ''.join([p.get('translation') or '' for p in pages])
            doc.translation = full_translation

            await db.flush()
            return {
                'page': target['page'],
                'translation': target['translation'],
            }

    @staticmethod
    async def compose_refined_markdown(*, pk: int) -> str:
        """
        基于 OCR 分页翻译结果，调用 AI 生成结构化的精炼 Markdown 内容。

        生成的 Markdown 包含按章节组织的结构，每章节包含：标题、关键词、简要概括、原文与翻译对照文本。
        原文使用普通正文，翻译使用 > 引用块，便于前端区分样式。

        :param pk: 文档ID
        :return: 生成的 Markdown 字符串
        """
        async with async_db_session.begin() as db:
            doc = await db.get(SysDoc, pk)
            if not doc:
                raise errors.NotFoundError(msg='文件不存在')

            pages = doc.ocr_pages_translation
            if not pages:
                return ''

            # 构建供 AI 处理的对照文本
            pairs = []
            for p in pages:
                page_num = p.get('page', 0)
                orig_text = p.get('text', '')
                trans_text = p.get('translation', '')
                if orig_text.strip() or trans_text.strip():
                    pairs.append(f"--- 第 {page_num} 页 ---\n原文：\n{orig_text}\n\n翻译：\n{trans_text}")

            input_text = '\n\n'.join(pairs)

            system_context = (
                "你是一个文档处理助手。请基于以下原文和翻译对照内容，生成结构清晰的 Markdown 文档。\n\n"
                "要求：\n"
                "1. 将内容按语义划分章节，每章节包含：\n"
                "   - ## 章节标题\n"
                "   - **关键词**：关键词列表\n"
                "   - **摘要**：该章节的简要概括\n"
                "   - 正文（原文在前，翻译用 > 引用块跟在原文下方）\n"
                "2. 原文段落使用普通 Markdown 正文，对应的翻译内容用 `> ` 引用块包裹\n"
                "3. 删除 OCR 产生的明显错误字符和无关页眉页脚\n"
                "4. 只输出 Markdown，不要额外解释\n"
                "5. 如果内容不足以划分章节，至少给出标题、关键词、摘要和正文"
            )
            user_prompt = f"请处理以下内容：\n\n{input_text}"

            result = await llm_service.get_llm_response(system_context, user_prompt)

            doc.refined_markdown = result
            await db.flush()

            return result

    @staticmethod
    async def base_update(pk: int, obj: dict) -> int:
        async with async_db_session.begin() as db:
            count = await sys_doc_dao.base_update(db, pk, obj)
            return count

    @staticmethod
    def _extract_from_workbook(workbook_json: str) -> tuple[list[dict], str]:
        """
        从 Univer IWorkbookData JSON 提取结构化行数据和纯文本内容。

        - 每个 Sheet 取第一非空行作为表头，后续行按 {列名: 值} 格式提取。
        - 多个 Sheet 的行顺序合并。
        - content 格式与 tabular_processor 保持一致：每行 "列名 值 列名 值\n"。
        """
        try:
            wb = json.loads(workbook_json)
        except Exception:
            return [], ''

        all_rows: list[dict] = []
        content_lines: list[str] = []

        sheets: dict = wb.get('sheets', {})
        sheet_order: list[str] = wb.get('sheetOrder', list(sheets.keys()))

        for sheet_id in sheet_order:
            sheet = sheets.get(sheet_id)
            if not sheet:
                continue
            cell_data: dict = sheet.get('cellData', {})
            if not cell_data:
                continue

            row_indices = sorted(int(r) for r in cell_data.keys())
            if not row_indices:
                continue

            # 第一行作为表头
            header_idx = row_indices[0]
            header_cells: dict = cell_data.get(str(header_idx), {})
            col_indices = sorted(int(c) for c in header_cells.keys())
            headers: dict[int, str] = {}
            for col_idx in col_indices:
                cell = header_cells.get(str(col_idx), {})
                val = cell.get('v', '')
                headers[col_idx] = str(val) if val is not None and val != '' else f'列{col_idx + 1}'

            # 数据行
            for row_idx in row_indices[1:]:
                row_cells: dict = cell_data.get(str(row_idx), {})
                row_dict: dict = {}
                for col_idx in col_indices:
                    cell = row_cells.get(str(col_idx), {})
                    val = cell.get('v', None)
                    row_dict[headers[col_idx]] = val
                # 跳过全空行
                if any(v is not None and v != '' for v in row_dict.values()):
                    all_rows.append(row_dict)
                    line = ' '.join(
                        f"{k} {v}" for k, v in row_dict.items() if v is not None and v != ''
                    )
                    content_lines.append(line)

        content = '\n'.join(content_lines)
        return all_rows, content

    @staticmethod
    async def update(*, pk: int, obj: UpdateSysDocParam) -> int:
        from backend.common.context import get_current_user
        from backend.database.db_pg import user_scoped_db_session
        current_user = get_current_user()

        # 如果携带 workbook，提前提取 content 和行数据（CPU 操作，不占 DB 连接）
        workbook_rows: list[dict] = []
        if obj.workbook:
            workbook_rows, extracted_content = SysDocService._extract_from_workbook(obj.workbook)
            obj = obj.model_copy(update={'content': extracted_content})

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

            # 原子替换 sys_doc_data（workbook 保存时同步更新行数据）
            if obj.workbook:
                await sys_doc_data_dao.delete(db, [pk])
                if workbook_rows:
                    param_list = [
                        CreateSysDocDataParam(doc_id=pk, row=r) for r in workbook_rows
                    ]
                    await sys_doc_data_dao.create_bulk(db, param_list)

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

        if not content or not content.strip():
            raise errors.ForbiddenError(msg='文档内容为空')

        from backend.common.context import get_current_user
        _extract_user = get_current_user()
        _extract_user_id = _extract_user.id if _extract_user else None

        # system_prompt 只需构建一次，与内容切块无关
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

        # 按段落切块：累加到接近 60000 tokens（≈120000 字符）时切断
        # 保留约 10000 tokens 给 system_prompt 和模型输出
        MAX_CHUNK_CHARS = 120_000
        paragraphs = re.split(r'\n{2,}', content)
        if len(paragraphs) <= 1:
            paragraphs = content.split('\n')

        content_chunks: list[str] = []
        current_parts: list[str] = []
        current_len = 0
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if current_len + len(para) > MAX_CHUNK_CHARS and current_parts:
                content_chunks.append('\n\n'.join(current_parts))
                current_parts = [para]
                current_len = len(para)
            else:
                current_parts.append(para)
                current_len += len(para)
        if current_parts:
            content_chunks.append('\n\n'.join(current_parts))

        if not content_chunks:
            return 0

        log.debug(f"[extract_entities] 文档 {pk} 共 {len(content_chunks)} 块，内容长度 {len(content)}")

        # 逐块调用 AI（在 DB session 外，避免长事务占用连接）
        # 按 (name, type) 去重，同名实体只保留首次出现
        all_entities_data: list[dict] = []
        seen_keys: set[tuple] = set()

        for idx, chunk in enumerate(content_chunks):
            log.debug(f"[extract_entities] 文档 {pk} 处理第 {idx + 1}/{len(content_chunks)} 块，块长 {len(chunk)}")
            user_prompt = f"请从以下文本中提取实体：\n\n{chunk}"
            try:
                response = await llm_service.get_llm_response(system_prompt, user_prompt)
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
                for entity_data in result.get("entities", []):
                    name = entity_data.get("name")
                    etype = entity_data.get("type")
                    if not name or not etype:
                        continue
                    key = (name, etype)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        all_entities_data.append(entity_data)

            except json.JSONDecodeError as e:
                log.warning(f"[extract_entities] 文档 {pk} 块 {idx + 1} JSON 解析失败: {repr(e)}")
            except Exception as e:
                log.warning(f"[extract_entities] 文档 {pk} 块 {idx + 1} AI 调用失败: {repr(e)}")

        if not all_entities_data:
            return 0

        log.debug(f"[extract_entities] 文档 {pk} 去重后共 {len(all_entities_data)} 个实体，开始入库")

        # 所有块处理完后统一入库（单事务）
        try:
            async with async_db_session.begin() as db:
                entity_count = 0
                for entity_data in all_entities_data:
                    entity_type_name = entity_data.get("type")
                    entity_name = entity_data.get("name")
                    entity_description = entity_data.get("description")
                    entity_properties = entity_data.get("properties", {})

                    if not entity_name or not entity_type_name:
                        continue

                    existing_entities = await db.execute(
                        select(Entity).where(
                            Entity.name == entity_name,
                            Entity.entity_type == entity_type_name
                        )
                    )
                    existing_entity = existing_entities.scalars().first()

                    if existing_entity:
                        if existing_entity.properties:
                            existing_entity.properties.update(entity_properties)
                        else:
                            existing_entity.properties = entity_properties
                        if entity_description and not existing_entity.description:
                            existing_entity.description = entity_description
                        entity_id = existing_entity.id
                    else:
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

                await db.execute(update(SysDoc).where(SysDoc.id == pk).values(entity_extracted=1))
                return entity_count

        except Exception as e:
            raise errors.ServerError(msg=f"实体入库失败: {repr(e)}")

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