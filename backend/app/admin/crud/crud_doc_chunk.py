#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model import SysDocChunk
from backend.app.admin.schema.doc_chunk import CreateSysDocChunkParam


class CRUDSysDocDChunk(CRUDPlus[SysDocChunk]):
    async def search_chunk_vector(self, db: AsyncSession, query_vector: list[float] = None, limit: int = 0)->SysDocChunk:
        # 构建向量搜索SQL

        vector_str = f"[{', '.join(map(str, query_vector))}]"

        sql = f"""
        SELECT id, doc_id,doc_name, chunk_text, chunk_embedding <-> :query_vector AS distance 
        FROM sys_doc_chunk
        WHERE chunk_embedding IS NOT NULL
        ORDER BY chunk_embedding <-> :query_vector 
        LIMIT :limit
        """
        
        result = await db.execute(
            text(sql),
            {
                "query_vector": vector_str,
                "limit": limit
            }
        )
        
        similar_docs = result.fetchall()
        
        return similar_docs

    async def get(self, db: AsyncSession, pk: int) -> SysDocChunk | None:
        """
        获取 SysDocChunk

        :param db:
        :param pk:
        :return:
        """
        return await self.select_model(db, pk)

    async def get_all(self, db: AsyncSession) -> Sequence[SysDocChunk]:
        """
        获取所有 SysDocChunk

        :param db:
        :return:
        """
        return await self.select_models(db)

    async def create(self, db: AsyncSession, obj_in: CreateSysDocChunkParam) -> SysDocChunk:
        """
        创建 SysDocChunk

        :param db:
        :param obj_in:
        :return:
        """
        return await self.create_model(db, obj_in)

    # async def update(self, db: AsyncSession, pk: int, obj_in: UpdateSysDocDataParam) -> int:
    #     """
    #     更新 SysDocData

    #     :param db:
    #     :param pk:
    #     :param obj_in:
    #     :return:
    #     """
    #     return await self.update_model(db, pk, obj_in)

    # async def delete(self, db: AsyncSession, pk: list[int]) -> int:
    #     """
    #     删除 SysDocData

    #     :param db:
    #     :param pk:
    #     :return:
    #     """
    #     return  await self.delete_model_by_column(db, allow_multiple=True, id__in=pk)


sys_doc_chunk_dao: CRUDSysDocDChunk = CRUDSysDocDChunk(SysDocChunk)
