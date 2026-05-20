#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence
import json
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model import SysDocEmbedding
from backend.app.admin.schema.doc_embdding import CreateSysDocEmbeddingParam


class CRUDSysDocEmbedding(CRUDPlus[SysDocEmbedding]):

    async def search_chunk_vector(
        self,
        db: AsyncSession,
        query_vector: list[float] = None,
        limit: int = 0,
        distance_threshold: float = None,
        doc_id: int = None,
        doc_ids: list[int] | None = None,
    ) -> list:
        """
        向量相似度搜索

        :param db: 数据库会话
        :param query_vector: 查询向量
        :param limit: 返回结果数量限制
        :param distance_threshold: 距离阈值，只返回距离小于此值的结果（距离越小越相似）
                                   建议值：0.8-1.5，默认为 1.2
        :param doc_id: 文档ID，如果指定则只搜索该文档的分块
        :param doc_ids: 文档 ID 列表（目录过滤），None 则不限，空列表直接返回空
        :return: 相似文档列表
        """
        # 构建向量搜索SQL语句
        if not query_vector or limit <= 0:
            return []
        if doc_ids is not None and not doc_ids:
            return []

        # 设置默认阈值
        if distance_threshold is None:
            distance_threshold = 1.2

        # 获取向量维度
        vector_dim = len(query_vector)
        # 根据维度选择对应的列名
        if vector_dim == 384:
            embedding_column = 'embedding_384'
        elif vector_dim == 768:
            embedding_column = 'embedding_768'
        elif vector_dim == 1536:
            embedding_column = 'embedding_1536'
        elif vector_dim == 3072:
            embedding_column = 'embedding_3072'
        else:
            # 默认使用1024维向量列
            embedding_column = 'embedding'

        vector_str = json.dumps(query_vector)

        # 构建WHERE条件
        where_conditions = [
            f"{embedding_column} IS NOT NULL",
            f"({embedding_column} <-> :query_vector) < :distance_threshold"
        ]
        params = {
            "query_vector": vector_str,
            "limit": limit,
            "distance_threshold": distance_threshold
        }

        if doc_id is not None:
            where_conditions.append("doc_id = :doc_id")
            params["doc_id"] = doc_id

        if doc_ids is not None:
            id_list = ','.join(str(int(d)) for d in doc_ids)
            where_conditions.append(f"doc_id = ANY(ARRAY[{id_list}]::bigint[])")

        where_clause = " AND ".join(where_conditions)

        # 添加距离阈值过滤条件
        sql = f"""
        SELECT id, chunk_id, doc_id, doc_name, chunk_text, {embedding_column} <-> :query_vector AS distance
        FROM sys_doc_embedding
        WHERE {where_clause}
        ORDER BY {embedding_column} <-> :query_vector
        LIMIT :limit
        """

        result = await db.execute(text(sql), params)

        similar_docs = result.fetchall()

        return similar_docs

    # async def get(self, db: AsyncSession, pk: int) -> SysDocEmbedding | None:
    #     """
    #     获取 SysDocChunk

    #     :param db:
    #     :param pk:
    #     :return:
    #     """
    #     return await self.select_model(db, pk)

    # async def get_all(self, db: AsyncSession) -> Sequence[SysDocEmbedding]:
    #     """
    #     获取所有 SysDocChunk

    #     :param db:
    #     :return:
    #     """
    #     return await self.select_models(db)

    async def create(self, db: AsyncSession, obj_in: CreateSysDocEmbeddingParam) -> SysDocEmbedding:
        """
        创建 SysDocEmbedding

        :param db:
        :param obj_in:
        :return:
        """
        return await self.create_model(db, obj_in)
    
    async def create_bulk(self, db: AsyncSession, obj_list: list[CreateSysDocEmbeddingParam]) -> list[SysDocEmbedding]:
        """
        批量创建 SysDocEmbedding
        :param db: 数据库会话
        :param obj_list: 要插入的对象列表
        :return: 插入后的 SysDo 列表
        """
        return await self.create_models(db,obj_list)
   

    # async def update(self, db: AsyncSession, pk: int, obj_in: UpdateSysDocDataParam) -> int:
    #     """
    #     更新 SysDocData

    #     :param db:
    #     :param pk:
    #     :param obj_in:
    #     :return:
    #     """
    #     return await self.update_model(db, pk, obj_in)

    async def delete(self, db: AsyncSession, doc_id: list[int]) -> int:
        """3
        删除 SysDocChunk

        :param db:
        :param pk:
        :return:
        """
        return  await self.delete_model_by_column(db, allow_multiple=True, doc_id__in=doc_id)


sys_doc_embedding_dao: CRUDSysDocEmbedding = CRUDSysDocEmbedding(SysDocEmbedding)
