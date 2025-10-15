#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from typing import Sequence
from sqlalchemy import Select, select, func, delete
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
from backend.app.admin.model import SysDocData,SysDocChunk
from backend.app.admin.model.sys_star_doc import sys_star_doc
from backend.app.admin.schema.doc import CreateSysDocParam, UpdateSysDocParam
from backend.common.exception import errors
from backend.database.db_pg import async_db_session
from backend.app.admin.schema.doc_data import CreateSysDocDataParam
from backend.app.admin.schema.doc_chunk import CreateSysDocChunkParam
from backend.app.admin.schema.doc_embdding import CreateSysDocEmbeddingParam
from backend.utils.doc_utils import request_text_to_vector
from backend.app.admin.service.llm_service import llm_service
from backend.utils.oss_client import minio_client
from backend.core.conf import settings
import asyncio
import jieba
import duckdb
import pandas as pd
import pyarrow.parquet as pq
from io import BytesIO

class SysDocService:

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
            
        # 配置知识图谱生成参数
        config = {
            "llm": {
                "model": "gpt-3.5-turbo",
                "max_tokens": 1000,
                "temperature": 0.7
            },
            "chunking": {
                "chunk_size": 1000,
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
        spo_list = await kg_service.generate_knowledge_graph(doc.content, config)
        if not spo_list:
            return []
            
        # 构建SPO对象列表
        spo_objects = []
        # 存储此文档相关的所有实体ID
        doc_entities = set()
        
        async with async_db_session.begin() as db:
            entity_cache = {}
            # 导入sys_entity_doc表以用于直接插入记录
            from backend.app.admin.model.sys_entity_doc import sys_entity_doc

            async def get_or_create_entity(name: str, entity_type: str) -> Entity:
                if name in entity_cache:
                    # 检查实体是否已经与文档关联
                    if entity_cache[name].id not in doc_entities:
                        doc_entities.add(entity_cache[name].id)
                        # 向sys_entity_doc表中插入记录，建立实体和文档的关系
                        await db.execute(
                            sys_entity_doc.insert().values(
                                entity_id=entity_cache[name].id,
                                doc_id=pk
                            )
                        )
                        await db.flush()
                    return entity_cache[name]
                
                # Check if entity exists
                stmt = select(Entity).where(Entity.name == name)
                result = await db.execute(stmt)
                entity = result.scalar_one_or_none()

                if not entity:
                    # Create entity
                    entity_to_create = Entity(name=name, entity_type=entity_type)
                    db.add(entity_to_create)
                    await db.flush()
                    await db.refresh(entity_to_create)
                    entity = entity_to_create
                
                # 记录实体ID并向sys_entity_doc表中插入记录
                if entity.id not in doc_entities:
                    doc_entities.add(entity.id)
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

    # @staticmethod
    # async def token_search(tokens: str = None) -> list[int]:
    #     async with async_db_session() as db:
    #         res = await sys_doc_dao.token_search(db, tokens)
    #         return res


    @staticmethod
    async def get_select(*, title: str = None, name: str = None, doc_type: str = None,
                          content: str = None, source: str = None, ids: list[int] = None, 
                          rangeValue: list[str]) -> Select:
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
        )

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
    async def search(*, tokens: str = None, page: int = None, size: int = None):
        cut = jieba.cut_for_search(tokens)
        seg_list = list(cut)  # 立即转换为列表
        # print("seg_list:", seg_list)
        async with async_db_session() as db:
            tokens = ' '.join(seg_list)
            res = await sys_doc_dao.search(db, tokens, page, size)
            items = res.get("items")
            for item in items:
                # 对每个文档的内容进行高亮处理
                hit = SysDocService.highlight_text_window(item.get("content"), seg_list)
                item["title"] = SysDocService.highlight_text(item.get("title"), seg_list)
                item["hit"] = hit
            return res

    @staticmethod
    async def similar_search(query: str = None, page: int = None, size: int = None):
        loop = asyncio.get_running_loop()
        text_emb = await loop.run_in_executor(None, request_text_to_vector, query)
        query_vector = text_emb[0]["embs"]
        async with async_db_session() as db:
            res = await sys_doc_dao.search_by_vector(db, query_vector, page, size)
            return res



    @staticmethod
    async def search_similar_docs(*, query_vector: list[float] = None, limit: int = None):
        async with async_db_session() as db:
            res = await sys_doc_embedding_dao.search_chunk_vector(db, query_vector, limit)
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


    @staticmethod
    async def create_doc_tokens(*, id: int) -> SysDoc:
        doc = await sys_doc_service.get(pk=id)
        title = doc.title
        content = doc.content
        title_tokens = ''
        content_tokens = ''
        loop = asyncio.get_event_loop()
        if title:
            a_seg_list = await loop.run_in_executor(None, jieba.cut, title)
            # a_seg_list = jieba.cut(title, cut_all=True)
            title_tokens =  " ".join(a_seg_list) + " " + doc.type
        if content:
            b_seg_list = await loop.run_in_executor(None, jieba.cut_for_search, content)
            # b_seg_list = jieba.cut_for_search(content)
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
    async def create_doc_bulk_embeddings(*, emb_list: list[CreateSysDocEmbeddingParam]) -> list[CreateSysDocEmbeddingParam]:
        async with async_db_session.begin() as db:
            return await sys_doc_embedding_dao.create_bulk(db, emb_list)

    @staticmethod
    async def base_update(pk: int, obj: dict) -> int:
        async with async_db_session.begin() as db:
            count = await sys_doc_dao.base_update(db, pk, obj)
            return count

    @staticmethod
    async def update(*, pk: int, obj: UpdateSysDocParam) -> int:
        async with async_db_session.begin() as db:
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
    async def get_count():
        async with async_db_session() as db:
            res = await sys_doc_dao.get_count(db)
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



sys_doc_service = SysDocService()