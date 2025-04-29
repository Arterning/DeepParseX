#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from sqlalchemy import Select

from backend.app.admin.crud.crud_doc import sys_doc_dao
from backend.app.admin.crud.crud_doc_data import sys_doc_data_dao
from backend.app.admin.crud.crud_doc_chunk import sys_doc_chunk_dao
from backend.app.admin.crud.crud_doc_embedding import sys_doc_embedding_dao
from backend.app.admin.model import SysDoc
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

    @staticmethod
    async def search(*, tokens: str = None):
        async with async_db_session() as db:
            res = await sys_doc_dao.search(db, tokens)
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
            await sys_doc_dao.update(db, pk, obj)


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
    async def update_account_pwd(*, pk: list[int], accounts: list[str]):
        async with async_db_session.begin() as db:
            count = await sys_doc_dao.update_account_pwd(db, pk,accounts)
            return count


    @staticmethod
    async def get_hot_docs(user_id: int = None) -> Sequence[SysDoc]:
        async with async_db_session() as db:
            docs = await sys_doc_dao.get_hot_docs(db, user_id=user_id)
            return docs

sys_doc_service = SysDocService()