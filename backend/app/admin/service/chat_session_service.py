#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from backend.app.admin.crud.crud_chat_session import chat_session_dao
from backend.app.admin.model.sys_chat_session import ChatSession
from backend.app.admin.schema.chat_session import CreateChatSessionParam, UpdateChatSessionParam
from backend.common.exception import errors
from backend.database.db_pg import async_db_session
from sqlalchemy import Select


class ChatSessionService:
    @staticmethod
    async def get(*, pk: int) -> ChatSession:
        async with async_db_session() as db:
            chat_session = await chat_session_dao.get(db, pk)
            if not chat_session:
                raise errors.NotFoundError(msg='不存在')
            return chat_session
    
    @staticmethod
    async def get_select() -> Select:
        return await chat_session_dao.get_list()

    @staticmethod
    async def get_all() -> Sequence[ChatSession]:
        async with async_db_session() as db:
            chat_sessions = await chat_session_dao.get_all(db)
            return chat_sessions

    @staticmethod
    async def create(*, obj: CreateChatSessionParam) -> None:
        async with async_db_session.begin() as db:
            await chat_session_dao.create(db, obj)

    @staticmethod
    async def update(*, pk: int, obj: UpdateChatSessionParam) -> int:
        async with async_db_session.begin() as db:
            count = await chat_session_dao.update(db, pk, obj)
            return count

    @staticmethod
    async def delete(*, pk: list[int]) -> int:
        async with async_db_session.begin() as db:
            count = await chat_session_dao.delete(db, pk)
            return count


chat_session_service = ChatSessionService()