#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from typing import Sequence
from datetime import datetime, timedelta
from sqlalchemy import bindparam, select, Select, text, desc, and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model import SysDoc
from backend.app.admin.schema.doc import CreateSysDocParam, UpdateSysDocParam


class CRUDSysDoc(CRUDPlus[SysDoc]):
    async def get(self, db: AsyncSession, pk: int) -> SysDoc | None:
        """
        获取 SysDoc

        :param db:
        :param pk:
        :return:
        """
        where = [self.model.id == pk]
        doc = await db.execute(
            select(self.model)
            .options(selectinload(self.model.doc_data))
            .options(selectinload(self.model.email_msg))
            .options(selectinload(self.model.doc_spos))
            .where(*where)
        )
        return doc.scalars().first()

    # async def token_search(self, db: AsyncSession, tokens: str = None) -> list[int]:
    #     if tokens:
    #         query = f"""
    #         SELECT DISTINCT doc_id
    #         FROM sys_doc_data
    #         WHERE to_tsvector('simple', tokens::text) @@ plainto_tsquery('{tokens}');
    #         """
    #         result = await db.execute(text(query))
    #         ids = result.scalars().all()
    #         print("token search ids", ids)
    #         return ids
    #     else:
    #         return None

    async def search_hit(self, db: AsyncSession, tokens: str = None):
        if tokens:
            query = f"""
            SELECT id, name, title, type,
            ts_headline('simple', doc_tokens, plainto_tsquery(:tokens)) AS hit
            FROM sys_doc
            WHERE doc_tokens @@ plainto_tsquery(:tokens);
            """
            result = await db.execute(text(query), {"tokens": tokens})
            # 使用 fetchall() 来获取完整的行
            docs = result.fetchall()  # 返回所有行

            # 将每一行转为字典格式，便于查看
            docs_list = [{
                "id": doc.id, 
                "name": doc.name, 
                "type": doc.type,
                "title": doc.title,
                "hit": doc.hit,
            } for doc in docs]
            
            return docs_list
        else:
            return []
    
    async def search(self, db: AsyncSession, tokens: str = None, page: int = None, size: int = None):
        # 初始化分页参数
        if page is None:
            page = 1
        if size is None:
            size = 10
            
        # 计算偏移量
        offset = (page - 1) * size

        if tokens:
            query = f"""
            SELECT id, name, title, type, content
            FROM sys_doc
            WHERE doc_tokens @@ plainto_tsquery(:tokens)
            LIMIT :limit OFFSET :offset;
            """
            result = await db.execute(
                text(query), 
                {"tokens": tokens, "limit": size, "offset": offset}
            )
            # 使用 fetchall() 来获取完整的行
            docs = result.fetchall()  # 返回所有行

            # 将每一行转为字典格式，便于查看
            docs_list = [{
                "id": doc.id, 
                "name": doc.name, 
                "type": doc.type,
                "title": doc.title,
                "content": doc.content
            } for doc in docs]

            # 执行总记录数查询
            count_query = f"""
            SELECT count(*)
            FROM sys_doc
            WHERE doc_tokens @@ plainto_tsquery(:tokens);
            """
            count_result = await db.execute(text(count_query), {"tokens": tokens})
            total = count_result.scalar()
            
            # 返回包含分页信息的结果
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
        
    async def search_by_vector(self, db: AsyncSession, query_vector: list[float] = None, limit: int = 0):
        # 构建向量搜索SQL

        # vector_str = f"[{', '.join(map(str, query_vector))}]"

        vector_str = json.dumps(query_vector)

        sql = f"""
        SELECT id, name, title, content, embedding <-> :query_vector AS distance 
        FROM sys_doc
        WHERE embedding IS NOT NULL
        ORDER BY embedding <-> :query_vector 
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


    async def get_list(self, name: str = None, doc_type: str = None,
                       title: str = None, source: str = None,
                        content: str = None, ids: list[int] = None,
                        start_time: str = None, end_time :str = None,
                        ) -> Select:
        """
        获取 SysDoc 列表
        :return:
        """
        where_list = []
        stmt = select(self.model).order_by(desc(self.model.created_time))
        if title is not None and title != '':
            where_list.append(self.model.title.like(f'%{title}%'))
        if name is not None and name != '':
            where_list.append(self.model.name.like(f'%{name}%'))
        if doc_type is not None:
            where_list.append(self.model.type == doc_type)
        # if tokens is not None and tokens != '':
        #     where_list.append(self.model.tokens.match(tokens))
        if content is not None and content != '':
            where_list.append(self.model.content.like(f'%{content}%'))
        if source is not None and source != '':
            where_list.append(self.model.source.like(f'%{source}%'))
        # if email_to is not None and email_to != '':
        #     where_list.append(self.model.email_to.like(f'%{email_to}%'))
        # if email_subject is not None and email_subject != '':
        #     where_list.append(self.model.email_subject.like(f'%{email_subject}%'))
        # if email_time is not None and email_time != '':
        #     where_list.append(self.model.email_time.like(f'%{email_time}%'))
        if start_time:
            start_dt = datetime.strptime(start_time, '%Y-%m-%d')
            where_list.append(self.model.doc_time >= start_dt)
        if end_time:
             # 将字符串转换为datetime对象，并设置时间为当天23:59:59
            end_dt = datetime.strptime(end_time, '%Y-%m-%d') + timedelta(hours=23, minutes=59, seconds=59)
            where_list.append(self.model.doc_time <= end_dt)
        if ids is not None:
            where_list.append(self.model.id.in_(ids))
        if where_list:
            stmt = stmt.where(and_(*where_list))
        return stmt

    async def get_all(self, db: AsyncSession) -> Sequence[SysDoc]:
        """
        获取所有 SysDoc

        :param db:
        :return:
        """
        return await self.select_models(db)
    
    from sqlalchemy.future import select


    async def get_column_data(self, db: AsyncSession, column: str):
        """
        获取指定列的所有数据

        :param db: AsyncSession
        :param column: 列名
        :return: 列的所有数据
        """
        stmt = select(getattr(SysDoc, column))  # 动态获取列名
        result = await db.execute(stmt)
        return result.scalars().all()  # 获取所有列数据并返回


    async def create(self, db: AsyncSession, obj_in: CreateSysDocParam) -> SysDoc:
        """
        创建 SysDoc

        :param db:
        :param obj_in:
        :return:
        """
        return await self.create_model(db, obj_in)

    async def update_tokens(self, db: AsyncSession, doc: SysDoc, title_tokens: str, content_tokens: str, doc_tokens: str):
        update_sql = """
            UPDATE sys_doc
            SET doc_vector = setweight(to_tsvector('simple', :title_tokens), 'A') ||
                        setweight(to_tsvector('simple', :content_tokens), 'B'),
                doc_tokens=:doc_tokens
            WHERE id = :doc_id
        """
        result = await db.execute(
            text(update_sql), 
            {
                "title_tokens": title_tokens,
                "content_tokens": content_tokens,
                "doc_tokens": doc_tokens,
                "doc_id": doc.id
            }
        )
        await db.commit()  # 提交事务
        return result


    async def update(self, db: AsyncSession, pk: int, obj_in: UpdateSysDocParam) -> int:
        """
        更新 SysDoc

        :param db:
        :param pk:
        :param obj_in:
        :return:
        """
        return await self.update_model(db, pk, obj_in)
    



    async def delete(self, db: AsyncSession, pk: list[int]) -> int:
        """
        删除 SysDoc

        :param db:
        :param pk:
        :return:
        """
        return  await self.delete_model_by_column(db, allow_multiple=True, id__in=pk)


    async def get_hot_docs(self, db: AsyncSession, user_id: int = None) -> Sequence[SysDoc]:
        docs = await db.execute(
             select(self.model)
            # .where(self.model.user_id==user_id)
            .order_by(self.model.created_time.desc())
            .limit(10)
        )
        return docs.scalars()


sys_doc_dao: CRUDSysDoc = CRUDSysDoc(SysDoc)
