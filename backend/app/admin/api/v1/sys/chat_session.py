#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.app.admin.schema.chat_session import (
    CreateChatSessionParam,
    GetChatSessionDetails,
    GetChatSessionListDetails,
    UpdateChatSessionParam,
)
from backend.app.admin.service.chat_session_service import chat_session_service
from backend.common.context import get_current_user
from backend.common.pagination import DependsPagination, paging_data
from backend.common.response.response_schema import ResponseModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db_pg import CurrentSession
from backend.utils.serializers import select_as_dict

router = APIRouter()


@router.get('/current-user-sessions', summary='获取当前用户所有会话', dependencies=[DependsJwtAuth])
async def get_current_user_sessions() -> ResponseModel:
    """
    获取当前登录用户的所有会话（包含完整 messages）
    """
    chat_sessions = await chat_session_service.get_current_user_sessions()
    data = [GetChatSessionListDetails(**select_as_dict(session)) for session in chat_sessions]
    return response_base.success(data=data)


@router.get('/{pk}', summary='获取详情', dependencies=[DependsJwtAuth])
async def get_chat_session(pk: Annotated[int, Path(...)]) -> ResponseModel:
    """
    获取单个会话详情（验证权限）
    """
    current_user = get_current_user()
    user_id = current_user.id if current_user else None
    chat_session = await chat_session_service.get(pk=pk, user_id=user_id)
    data = GetChatSessionDetails(**select_as_dict(chat_session))
    return response_base.success(data=data)


@router.get(
    '',
    summary='（模糊条件）分页获取当前用户会话',
    dependencies=[
        DependsJwtAuth,
        DependsPagination,
    ],
)
async def get_pagination_chat_session(db: CurrentSession) -> ResponseModel:
    """
    分页获取当前用户的会话列表
    """
    current_user = get_current_user()
    user_id = current_user.id if current_user else None
    chat_session_select = await chat_session_service.get_select(user_id=user_id)
    page_data = await paging_data(db, chat_session_select, GetChatSessionListDetails)
    return response_base.success(data=page_data)


@router.post(
    '',
    summary='创建会话',
    dependencies=[
        DependsJwtAuth,
    ],
)
async def create_chat_session(obj: CreateChatSessionParam) -> ResponseModel:
    """
    创建空会话
    """
    chat_session = await chat_session_service.create(obj=obj)
    data = GetChatSessionDetails(**select_as_dict(chat_session))
    return response_base.success(data=data)


@router.put(
    '/{pk}',
    summary='更新会话',
    dependencies=[
        DependsJwtAuth,
    ],
)
async def update_chat_session(pk: Annotated[int, Path(...)], obj: UpdateChatSessionParam) -> ResponseModel:
    """
    更新会话（包括 messages）
    """
    count = await chat_session_service.update(pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail(msg='更新失败或无权访问')


@router.delete(
    '',
    summary='（批量）删除会话',
    dependencies=[
        DependsJwtAuth,
    ],
)
async def delete_chat_session(pk: Annotated[list[int], Query(...)]) -> ResponseModel:
    """
    删除会话（只能删除自己的）
    """
    count = await chat_session_service.delete(pk=pk)
    if count > 0:
        return response_base.success()
    return response_base.fail(msg='删除失败或无权访问')