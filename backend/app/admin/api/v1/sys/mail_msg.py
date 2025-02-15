#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.app.admin.schema.mail_msg import CreateMailMsgParam, GetMailMsgListDetails, UpdateMailMsgParam
from backend.app.admin.service.mail_msg_service import mail_msg_service
from backend.common.pagination import DependsPagination, paging_data
from backend.common.response.response_schema import ResponseModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db_pg import CurrentSession

router = APIRouter()


@router.get('/{pk}', summary='获取详情', dependencies=[DependsJwtAuth])
async def get_mail_msg(pk: Annotated[int, Path(...)]) -> ResponseModel:
    mail_msg = await mail_msg_service.get(pk=pk)
    return response_base.success(data=mail_msg)


@router.get(
    '',
    summary='（模糊条件）分页获取所有',
    dependencies=[
        DependsJwtAuth,
        DependsPagination,
    ],
)
async def get_pagination_mail_msg(db: CurrentSession) -> ResponseModel:
    mail_msg_select = await mail_msg_service.get_select()
    page_data = await paging_data(db, mail_msg_select, GetMailMsgListDetails)
    return response_base.success(data=page_data)


@router.post(
    '',
    summary='创建',
    dependencies=[
        Depends(RequestPermission(':add')),
        DependsRBAC,
    ],
)
async def create_mail_msg(obj: CreateMailMsgParam) -> ResponseModel:
    await mail_msg_service.create(obj=obj)
    return response_base.success()


@router.put(
    '/{pk}',
    summary='更新',
    dependencies=[
        Depends(RequestPermission(':edit')),
        DependsRBAC,
    ],
)
async def update_mail_msg(pk: Annotated[int, Path(...)], obj: UpdateMailMsgParam) -> ResponseModel:
    count = await mail_msg_service.update(pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete(
    '',
    summary='（批量）删除',
    dependencies=[
        Depends(RequestPermission(':del')),
        DependsRBAC,
    ],
)
async def delete_mail_msg(pk: Annotated[list[int], Query(...)]) -> ResponseModel:
    count = await mail_msg_service.delete(pk=pk)
    if count > 0:
        return response_base.success()
    return response_base.fail()