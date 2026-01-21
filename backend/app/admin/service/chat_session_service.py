#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from sqlalchemy import Select, delete

from backend.app.admin.crud.crud_chat_session import chat_session_dao
from backend.app.admin.model.sys_chat_session import ChatSession
from backend.app.admin.model.sys_chat_message import ChatMessage
from backend.app.admin.schema.chat_session import CreateChatSessionParam, UpdateChatSessionParam
from backend.common.exception import errors
from backend.common.context import get_current_user
from backend.database.db_pg import async_db_session


class ChatSessionService:
    @staticmethod
    async def get(*, pk: int, user_id: int | None = None) -> ChatSession:
        """
        获取会话详情

        :param pk: 会话ID
        :param user_id: 用户ID，如果提供则验证权限
        :return:
        """
        async with async_db_session() as db:
            if user_id is not None:
                chat_session = await chat_session_dao.get_with_user_check(db, pk, user_id)
            else:
                chat_session = await chat_session_dao.get(db, pk)
            if not chat_session:
                raise errors.NotFoundError(msg='会话不存在或无权访问')
            return chat_session

    @staticmethod
    async def get_select(*, user_id: int | None = None) -> Select:
        """
        获取会话列表查询（用于分页）

        :param user_id: 用户ID，如果提供则只返回该用户的会话
        :return:
        """
        return await chat_session_dao.get_list(user_id=user_id)

    @staticmethod
    async def get_all() -> Sequence[ChatSession]:
        async with async_db_session() as db:
            chat_sessions = await chat_session_dao.get_all(db)
            return chat_sessions

    @staticmethod
    async def get_current_user_sessions() -> Sequence[ChatSession]:
        """
        获取当前登录用户的所有会话（包含 messages）

        :return:
        """
        current_user = get_current_user()
        if not current_user:
            raise errors.AuthorizationError(msg='未登录')

        async with async_db_session() as db:
            chat_sessions = await chat_session_dao.get_user_sessions(db, current_user.id)
            return chat_sessions

    @staticmethod
    async def create(*, obj: CreateChatSessionParam) -> ChatSession:
        """
        创建会话（空会话）

        :param obj: 创建参数
        :return: 创建的会话对象（包含ID）
        """
        # 从上下文获取当前用户并设置 create_user
        current_user = get_current_user()
        if current_user:
            obj.create_user = current_user.id

        async with async_db_session.begin() as db:
            chat_session = await chat_session_dao.create(db, obj)
            await db.flush()  # 确保获取到 ID
            await db.refresh(chat_session)  # 刷新以获取关系数据
            return chat_session

    @staticmethod
    async def update(*, pk: int, obj: UpdateChatSessionParam) -> int:
        """
        更新会话（包括 messages）

        :param pk: 会话ID
        :param obj: 更新参数
        :return: 更新的记录数
        """
        # 从上下文获取当前用户
        current_user = get_current_user()
        if current_user:
            obj.update_user = current_user.id

        async with async_db_session.begin() as db:
            # 验证会话所属用户
            if current_user:
                chat_session = await chat_session_dao.get_with_user_check(db, pk, current_user.id)
            else:
                chat_session = await chat_session_dao.get(db, pk)

            if not chat_session:
                raise errors.NotFoundError(msg='会话不存在或无权访问')

            # 如果有 messages，删除旧的并创建新的
            if obj.messages is not None:
                # 删除旧的 messages
                await db.execute(delete(ChatMessage).where(ChatMessage.session_id == pk))
                await db.flush()

                # 创建新的 messages
                for msg_param in obj.messages:
                    # 处理 chunks：将 Pydantic 对象转换为字典列表
                    chunks_data = None
                    if msg_param.chunks:
                        chunks_data = [chunk.model_dump() for chunk in msg_param.chunks]

                    new_message = ChatMessage(
                        sender=msg_param.sender,
                        content=msg_param.content,
                        chunks=chunks_data,
                        session_id=pk,
                        create_user=current_user.id if current_user else None
                    )
                    db.add(new_message)

                # 从更新参数中移除 messages（因为已经手动处理）
                update_data = obj.model_dump(exclude={'messages'}, exclude_unset=True)
                obj = UpdateChatSessionParam(**update_data)

            # 更新会话本身
            count = await chat_session_dao.update(db, pk, obj)
            return count

    @staticmethod
    async def delete(*, pk: list[int]) -> int:
        """
        删除会话（验证权限）

        :param pk: 会话ID列表
        :return: 删除的记录数
        """
        # 从上下文获取当前用户
        current_user = get_current_user()

        async with async_db_session.begin() as db:
            if current_user:
                # 只能删除自己的会话
                count = await chat_session_dao.delete_user_sessions(db, pk, current_user.id)
            else:
                # 如果没有当前用户（可能是管理员操作），允许删除所有
                count = await chat_session_dao.delete(db, pk)
            return count


chat_session_service = ChatSessionService()