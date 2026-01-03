#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from sqlalchemy import delete, Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model.sys_chat_session import ChatSession
from backend.app.admin.schema.chat_session import CreateChatSessionParam, UpdateChatSessionParam


class CRUDChatSession(CRUDPlus[ChatSession]):
    async def get(self, db: AsyncSession, pk: int) -> ChatSession | None:
        """
        获取 ChatSession

        :param db:
        :param pk:
        :return:
        """
        return await self.select_model(db, pk)

    async def get_list(self) -> Select:
        """
        获取聊天会话列表

        :return:
        """
        return await self.select_order('created_time', 'desc')

    async def get_all(self, db: AsyncSession) -> Sequence[ChatSession]:
        """
        获取所有 ChatSession

        :param db:
        :return:
        """
        return await self.select_models(db)

    async def create(self, db: AsyncSession, obj_in: CreateChatSessionParam) -> None:
        """
        创建 ChatSession

        :param db:
        :param obj_in:
        :return:
        """
        await self.create_model(db, obj_in)

    async def update(self, db: AsyncSession, pk: int, obj_in: UpdateChatSessionParam) -> int:
        """
        更新 ChatSession

        :param db:
        :param pk:
        :param obj_in:
        :return:
        """
        return await self.update_model(db, pk, obj_in)

    async def delete(self, db: AsyncSession, pk: list[int]) -> int:
        """
        删除 ChatSession

        :param db:
        :param pk:
        :return:
        """
        return  await self.delete_model_by_column(db, allow_multiple=True, id__in=pk)


chat_session_dao: CRUDChatSession = CRUDChatSession(ChatSession)