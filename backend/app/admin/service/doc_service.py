#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from typing import Sequence
from sqlalchemy import Select
from typing import List

from backend.app.admin.service.knowledge_graph.kg_service import kg_service
from backend.app.admin.crud.crud_doc import sys_doc_dao
from backend.app.admin.crud.crud_doc_data import sys_doc_data_dao
from backend.app.admin.crud.crud_doc_chunk import sys_doc_chunk_dao
from backend.app.admin.crud.crud_doc_embedding import sys_doc_embedding_dao
from backend.app.admin.model import SysDoc
from backend.app.admin.model import SubjectPredictObject
from backend.app.admin.model import SysDocData,SysDocChunk
from backend.app.admin.schema.doc import CreateSysDocParam, UpdateSysDocParam
from backend.common.exception import errors
from backend.database.db_pg import async_db_session
from backend.app.admin.schema.doc_data import CreateSysDocDataParam
from backend.app.admin.schema.doc_chunk import CreateSysDocChunkParam
from backend.app.admin.schema.doc_embdding import CreateSysDocEmbeddingParam
import asyncio
import jieba

class SysDocService:

    @staticmethod
    async def build_graph(*, pk: int):
        """构建文件的知识图谱
        
        Args:
            pk (int): 文档ID
            
        Returns:
            list[SubjectPredictObject]: 生成的知识图谱三元组列表
        """
        # 获取文档
        doc = await sys_doc_service.get(pk=pk)
        if not doc.content:
            return []
            
        # 配置知识图谱生成参数
        config = {
            "llm": {
                "model": "gpt-3.5-turbo",
                "max_tokens": 1000,
                "temperature": 0.7
            },
            "chunking": {
                "chunk_size": 500,
                "overlap": 50
            },
            "standardization": {
                "enabled": True
            },
            "inference": {
                "enabled": False
            }
        }
        
        # 生成知识图谱
        spo_list = kg_service.generate_knowledge_graph(doc.content, config)
        if not spo_list:
            return []
            
        # 构建SPO对象列表
        spo_objects = []
        async with async_db_session.begin() as db:
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

    # @staticmethod
    # async def token_search(tokens: str = None) -> list[int]:
    #     async with async_db_session() as db:
    #         res = await sys_doc_dao.token_search(db, tokens)
    #         return res


    @staticmethod
    async def get_select(*, name: str = None, type: str = None, email_from: str = None,
                         email_subject: str = None, email_time: str = None, email_to: str = None,
                          tokens: str = None, likeq: str = None, ids: list[int] = None) -> Select:
        return await sys_doc_dao.get_list(name=name, type=type, tokens=tokens, email_subject=email_subject,
                                          email_time=email_time, email_to=email_to,
                                          likeq=likeq, ids=ids, email_from=email_from)

    def highlight_text(original: str, keywords: List[str], start_tag='<b>', end_tag='</b>') -> str:
        sorted_keywords = sorted(keywords, key=len, reverse=True)
        for kw in sorted_keywords:
            pattern = re.escape(kw)
            original = re.sub(pattern, f'{start_tag}{kw}{end_tag}', original)
        return original
    
    def highlight_text_window(
        original: str, 
        keywords: List[str], 
        start_tag='<b>', 
        end_tag='</b>', 
        window=30, 
        max_snippets=3
    ) -> str:
        # 合并所有关键词构造整体正则模式
        sorted_keywords = sorted(set(keywords), key=len, reverse=True)
        keyword_pattern = '|'.join(map(re.escape, sorted_keywords))

        matches = list(re.finditer(keyword_pattern, original))
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
            def replacer(match):
                return f"{start_tag}{match.group(0)}{end_tag}"

            highlighted = re.sub(keyword_pattern, replacer, snippet)
            snippets.append(highlighted)

        return " ... ".join(snippets)


    
    @staticmethod
    async def search(*, tokens: str = None):
        cut = jieba.cut_for_search(tokens)
        seg_list = list(cut)  # 立即转换为列表
        # print("seg_list:", seg_list)
        async with async_db_session() as db:
            tokens = ' '.join(seg_list)
            res = await sys_doc_dao.search(db, tokens)
            for item in res:
                # 对每个文档的内容进行高亮处理
                hit = SysDocService.highlight_text_window(item.get("content"), seg_list)
                item["title"] = SysDocService.highlight_text(item.get("title"), seg_list)
                item["hit"] = hit
            return res

    @staticmethod
    async def search_by_vector(*, query_vector: list[float] = None, limit: int = 0):
        async with async_db_session() as db:
            res = await sys_doc_dao.search_by_vector(db, query_vector, limit)
            return res

    @staticmethod
    async def search_chunk_vector(*, query_vector: list[float] = None, limit: int = 0):
        async with async_db_session() as db:
            res = await sys_doc_chunk_dao.search_chunk_vector(db, query_vector, limit)
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
            # sys_doc = await sys_doc_dao.get_by_name(db, obj.name)
            # if sys_doc:
            #     raise errors.ForbiddenError(msg='文件已存在')
            doc = await sys_doc_dao.create(db, obj)
            return doc


    @staticmethod
    async def create_doc_tokens(*, id: int) -> SysDoc:
        doc = await sys_doc_service.get(pk=id)
        title = doc.title
        content = doc.content
        title_tokens = ''
        content_tokens = ''
        if title:
            a_seg_list = jieba.cut(title, cut_all=True)
            title_tokens =  " ".join(a_seg_list) + " " + doc.type
        if content:
            b_seg_list = jieba.cut_for_search(content)
            content_tokens = " ".join(b_seg_list)
        all_tokens = title_tokens + " " + content_tokens
        async with async_db_session() as db:
            res = await sys_doc_dao.update_tokens(db, doc, title_tokens, content_tokens, all_tokens)
            return res
        return doc

    @staticmethod
    async def create_doc_data(*, obj_list: CreateSysDocDataParam) -> SysDocData:
        async with async_db_session.begin() as db:
            return await sys_doc_data_dao.create_bulk(db, obj_list)
    
    @staticmethod
    # 批量插入
    async def create_doc_bulk_chunks(*, obj_list: list[CreateSysDocChunkParam]) -> list[SysDocChunk]:
        async with async_db_session.begin() as db:
            return await sys_doc_chunk_dao.create_bulk(db, obj_list)

    @staticmethod
    # 插入一个chunk
    async def create_doc_chunk(*, obj: CreateSysDocDataParam):
        async with async_db_session.begin() as db:
            return await sys_doc_chunk_dao.create(db, obj)
    
    @staticmethod
    # 批量插入
    async def create_doc_bulk_embedding(*, obj_list: list[CreateSysDocEmbeddingParam]) -> list[CreateSysDocEmbeddingParam]:
        async with async_db_session.begin() as db:
            return await sys_doc_embedding_dao.create_bulk(db, obj_list)
        
    @staticmethod
    async def update(*, pk: int, obj: UpdateSysDocParam) -> int:
        async with async_db_session.begin() as db:
            return await sys_doc_dao.update(db, pk, obj)


    @staticmethod
    async def  delete(*, pk: list[int]) -> int:
        async with async_db_session.begin() as db:
            count = await sys_doc_dao.delete(db, pk)
            return count

    @staticmethod
    async def  delete_doc_data(*, doc_id: list[int]) -> int:
        async with async_db_session.begin() as db:
            count = await sys_doc_data_dao.delete(db, doc_id)
            return count
        
    @staticmethod
    async def  delete_doc_chunk(*, doc_id: list[int]) -> int:
        async with async_db_session.begin() as db:
            count = await sys_doc_chunk_dao.delete(db, doc_id)
            return count
        

    @staticmethod
    async def get_hot_docs(user_id: int = None) -> Sequence[SysDoc]:
        async with async_db_session() as db:
            docs = await sys_doc_dao.get_hot_docs(db, user_id=user_id)
            return docs

sys_doc_service = SysDocService()