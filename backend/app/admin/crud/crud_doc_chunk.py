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

            # 先按文档分组分页，再取对应文档下的所有匹配 chunks
            query = f"""
            WITH ranked_docs AS (
                SELECT
                    c.doc_id,
                    MAX({rank_expr}) as max_rank
                FROM sys_doc_chunk c
                WHERE {where_clause}
                GROUP BY c.doc_id
                ORDER BY max_rank DESC
                LIMIT :limit OFFSET :offset
            )
            SELECT
                c.id as chunk_id,
                c.doc_id,
                c.chunk_index,
                c.chunk_text,
                c.chunk_translation,
                d.title as doc_title,
                d.name as doc_name,
                d.type as doc_type,
                ts_headline('simple', c.chunk_text, plainto_tsquery('simple', :tokens),
                           'StartSel=<mark>, StopSel=</mark>, MaxWords=50, MinWords=20, MaxFragments=3')
                AS highlight,
                {rank_expr} as rank,
                rd.max_rank
            FROM sys_doc_chunk c
            JOIN sys_doc d ON c.doc_id = d.id
            JOIN ranked_docs rd ON c.doc_id = rd.doc_id
            WHERE {where_clause}
            ORDER BY rd.max_rank DESC, c.doc_id, c.chunk_index;
            """

            result = await db.execute(
                text(query),
                {"tokens": tokens, "limit": size, "offset": offset}
            )
            chunks = result.fetchall()

            # 将结果转换为字典列表，按文档分组（顺序已由 SQL 保证）
            from collections import OrderedDict
            docs_dict = OrderedDict()

            for chunk in chunks:
                doc_id = chunk.doc_id
                if doc_id not in docs_dict:
                    docs_dict[doc_id] = {
                        'doc_id': doc_id,
                        'doc_title': chunk.doc_title,
                        'doc_name': chunk.doc_name,
                        'doc_type': chunk.doc_type,
                        'chunks': [],
                        'max_rank': float(chunk.max_rank) if chunk.max_rank else 0
                    }

                docs_dict[doc_id]['chunks'].append({
                    'chunk_id': chunk.chunk_id,
                    'chunk_index': chunk.chunk_index,
                    'chunk_text': chunk.chunk_text,
                    'highlight': chunk.highlight,
                    'rank': float(chunk.rank) if chunk.rank else 0
                })

            docs_list = list(docs_dict.values())

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

    async def search_doc_ids_by_keyword(
        self,
        db: AsyncSession,
        keyword: str,
        limit: int = 20
    ) -> list[dict]:
        """
        通过全文检索搜索包含关键词的文档ID及命中的分块内容（按相关度排序）

        :param db: 数据库会话
        :param keyword: 搜索关键词
        :param limit: 最大返回分块数量
        :return: [{'doc_id': int, 'doc_title': str, 'chunks': [str, ...]}]
        """
        if not keyword:
            return []

        sql = """
        SELECT c.doc_id, d.title AS doc_title, c.chunk_text
        FROM sys_doc_chunk c
        JOIN sys_doc d ON c.doc_id = d.id
        WHERE c.chunk_vector @@ plainto_tsquery('simple', :keyword)
        ORDER BY ts_rank(c.chunk_vector, plainto_tsquery('simple', :keyword)) DESC
        LIMIT :limit
        """
        result = await db.execute(text(sql), {"keyword": keyword, "limit": limit})
        rows = result.fetchall()

        # 按 doc_id 分组
        from collections import OrderedDict
        docs = OrderedDict()
        for row in rows:
            if row.doc_id not in docs:
                docs[row.doc_id] = {'doc_id': row.doc_id, 'doc_title': row.doc_title, 'chunks': []}
            docs[row.doc_id]['chunks'].append(row.chunk_text)

        return list(docs.values())

    async def update_chunk_translation(
        self,
        db: AsyncSession,
        chunk_id: int,
        chunk_translation: str
    ):
        """
        更新分块的翻译内容

        :param db: 数据库会话
        :param chunk_id: 分块ID
        :param chunk_translation: 翻译内容
        :return:
        """
        chunk = await db.get(self.model, chunk_id)
        if chunk:
            chunk.chunk_translation = chunk_translation
            await db.flush()
        return chunk

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
