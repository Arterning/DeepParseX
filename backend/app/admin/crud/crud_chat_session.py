#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from sqlalchemy import delete, Select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model.sys_chat_session import ChatSession
from backend.app.admin.schema.chat_session import CreateChatSessionParam, UpdateChatSessionParam


class CRUDChatSession(CRUDPlus[ChatSession]):
    async def get(self, db: AsyncSession, pk: int) -> ChatSession | None:
        """
        获取 ChatSession（包含 messages）

        :param db:
        :param pk:
        :return:
        """
        return await self.select_model_by_column(
            db,
            id=pk,
            options=[selectinload(ChatSession.messages)]
        )

    async def get_with_user_check(self, db: AsyncSession, pk: int, user_id: int) -> ChatSession | None:
        """
        获取 ChatSession 并验证所属用户（包含 messages）

        :param db:
        :param pk:
        :param user_id:
        :return:
        """
        return await self.select_model_by_column(
            db,
            id=pk,
            create_user=user_id,
            options=[selectinload(ChatSession.messages)]
        )

    async def get_list(self, user_id: int | None = None) -> Select:
        """
        获取聊天会话列表

        :param user_id: 用户ID，如果提供则只返回该用户的会话
        :return:
        """
        stmt = await self.select_order('created_time', 'desc')
        if user_id is not None:
            stmt = stmt.where(ChatSession.create_user == user_id)
        return stmt

    async def get_all(self, db: AsyncSession) -> Sequence[ChatSession]:
        """
        获取所有 ChatSession

        :param db:
        :return:
        """
        return await self.select_models(db)

    async def get_user_sessions(self, db: AsyncSession, user_id: int) -> Sequence[ChatSession]:
        """
        获取当前用户的所有会话（包含 messages）

        :param db:
        :param user_id:
        :return:
        """
        return await self.select_models_by_column(
            db,
            create_user=user_id,
            order_by_columns=['created_time'],
            order_by_direction='desc',
            options=[selectinload(ChatSession.messages)]
        )

    async def create(self, db: AsyncSession, obj_in: CreateChatSessionParam) -> ChatSession:
        """
        创建 ChatSession

        :param db:
        :param obj_in:
        :return:
        """
        return await self.create_model(db, obj_in)

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
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pk)

    async def delete_user_sessions(self, db: AsyncSession, pk: list[int], user_id: int) -> int:
        """
        删除用户的 ChatSession（验证权限）

        :param db:
        :param pk:
        :param user_id:
        :return:
        """
        return await self.delete_model_by_column(
            db,
            allow_multiple=True,
            id__in=pk,
            create_user=user_id
        )


chat_session_dao: CRUDChatSession = CRUDChatSession(ChatSession)