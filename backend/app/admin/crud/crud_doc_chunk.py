#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence
from sqlalchemy import select, text, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model.sys_doc_chunk import SysDocChunk
from backend.app.admin.schema.doc_chunk import CreateSysDocChunkParam, UpdateSysDocChunkParam


class CRUDSysDocChunk(CRUDPlus[SysDocChunk]):
    async def get_by_doc_id(self, db: AsyncSession, doc_id: int) -> Sequence[SysDocChunk]:
        """
        根据文档ID获取所有分块

        :param db:
        :param doc_id:
        :return:
        """
        stmt = (
            select(self.model)
            .where(self.model.doc_id == doc_id)
            .order_by(self.model.chunk_index)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def create_bulk(self, db: AsyncSession, objs: list[CreateSysDocChunkParam]) -> list[SysDocChunk]:
        """
        批量创建分块

        :param db:
        :param objs:
        :return:
        """
        chunks = [self.model(**obj.model_dump()) for obj in objs]
        db.add_all(chunks)
        await db.flush()
        return chunks

    async def delete_by_doc_id(self, db: AsyncSession, doc_ids: list[int]) -> int:
        """
        根据文档ID删除所有分块

        :param db:
        :param doc_ids:
        :return:
        """
        return await self.delete_model_by_column(db, allow_multiple=True, doc_id__in=doc_ids)

    async def search_chunks(
        self,
        db: AsyncSession,
        tokens: str = None,
        page: int = 1,
        size: int = 10,
        search_translation: bool = False
    ):
        """
        在分块中搜索

        :param db: 数据库会话
        :param tokens: 搜索关键词
        :param page: 页码
        :param size: 每页大小
        :param search_translation: 是否同时搜索翻译内容
        :return: 搜索结果
        """
        offset = (page - 1) * size

        if tokens:
            # 构建搜索条件
            vector_column = 'chunk_vector'
            text_column = 'chunk_text'

            if search_translation:
                # 同时搜索原文和翻译
                where_clause = """
                (chunk_vector @@ plainto_tsquery('simple', :tokens)
                 OR chunk_translation_vector @@ plainto_tsquery('simple', :tokens))
                """
                rank_expr = """
                GREATEST(
                    ts_rank(chunk_vector, plainto_tsquery('simple', :tokens)),
                    ts_rank(chunk_translation_vector, plainto_tsquery('simple', :tokens))
                )
                """
            else:
                # 只搜索原文
                where_clause = "chunk_vector @@ plainto_tsquery('simple', :tokens)"
                rank_expr = "ts_rank(chunk_vector, plainto_tsquery('simple', :tokens))"

            # 查询分块，并关联文档信息
            query = f"""
            SELECT
                c.id as chunk_id,
                c.doc_id,
                c.chunk_index,
                c.chunk_text,
                c.chunk_translation,
                d.id as doc_id,
                d.title as doc_title,
                d.name as doc_name,
                d.type as doc_type,
                ts_headline('simple', c.chunk_text, plainto_tsquery('simple', :tokens),
                           'StartSel=<mark>, StopSel=</mark>, MaxWords=50, MinWords=20, MaxFragments=3')
                AS highlight,
                {rank_expr} as rank
            FROM sys_doc_chunk c
            JOIN sys_doc d ON c.doc_id = d.id
            WHERE {where_clause}
            ORDER BY rank DESC, c.doc_id, c.chunk_index
            LIMIT :limit OFFSET :offset;
            """

            result = await db.execute(
                text(query),
                {"tokens": tokens, "limit": size, "offset": offset}
            )
            chunks = result.fetchall()

            # 将结果转换为字典列表，并按文档分组
            from collections import defaultdict
            docs_dict = defaultdict(lambda: {
                'doc_id': None,
                'doc_title': None,
                'doc_name': None,
                'doc_type': None,
                'chunks': [],
                'max_rank': 0
            })

            for chunk in chunks:
                doc_id = chunk.doc_id
                if docs_dict[doc_id]['doc_id'] is None:
                    docs_dict[doc_id]['doc_id'] = chunk.doc_id
                    docs_dict[doc_id]['doc_title'] = chunk.doc_title
                    docs_dict[doc_id]['doc_name'] = chunk.doc_name
                    docs_dict[doc_id]['doc_type'] = chunk.doc_type

                docs_dict[doc_id]['chunks'].append({
                    'chunk_id': chunk.chunk_id,
                    'chunk_index': chunk.chunk_index,
                    'chunk_text': chunk.chunk_text,
                    'highlight': chunk.highlight,
                    'rank': float(chunk.rank) if chunk.rank else 0
                })

                # 记录最高相关度
                rank = float(chunk.rank) if chunk.rank else 0
                if rank > docs_dict[doc_id]['max_rank']:
                    docs_dict[doc_id]['max_rank'] = rank

            # 转换为列表并按最高相关度排序
            docs_list = list(docs_dict.values())
            docs_list.sort(key=lambda x: x['max_rank'], reverse=True)

            # 计算总数
            count_query = f"""
            SELECT COUNT(DISTINCT c.doc_id)
            FROM sys_doc_chunk c
            WHERE {where_clause};
            """
            count_result = await db.execute(text(count_query), {"tokens": tokens})
            total = count_result.scalar() or 0

            return {
                "items": docs_list,
                "page": page,
                "size": size,
                "total": total
            }
        else:
            return {
                "items": [],
                "page": page,
                "size": size,
                "total": 0
            }

    async def update_chunk_vector(
        self,
        db: AsyncSession,
        chunk_id: int,
        chunk_vector_str: str,
        is_translation: bool = False
    ):
        """
        更新分块的分词向量

        :param db: 数据库会话
        :param chunk_id: 分块ID
        :param chunk_vector_str: tsvector 格式字符串
        :param is_translation: 是否更新翻译向量
        :return:
        """
        vector_column = 'chunk_translation_vector' if is_translation else 'chunk_vector'

        update_sql = f"""
            UPDATE sys_doc_chunk
            SET {vector_column} = CAST(:vector_str AS tsvector)
            WHERE id = :chunk_id
        """
        result = await db.execute(
            text(update_sql),
            {
                "vector_str": chunk_vector_str,
                "chunk_id": chunk_id
            }
        )
        return result


sys_doc_chunk_dao: CRUDSysDocChunk = CRUDSysDocChunk(SysDocChunk)
