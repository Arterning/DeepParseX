#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.app.admin.schema.mail_box import CreateMailBoxParam, GetMailBoxDetails, GetMailBoxListDetails, UpdateMailBoxParam
from backend.app.admin.service.mail_box_service import mail_box_service
from backend.common.pagination import DependsPagination, paging_data
from backend.common.response.response_schema import ResponseModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db_pg import CurrentSession
from backend.utils.serializers import select_as_dict

router = APIRouter()


@router.get('/{pk}', summary='获取详情', dependencies=[DependsJwtAuth])
async def get_mail_box(pk: Annotated[int, Path(...)]) -> ResponseModel:
    mail_box = await mail_box_service.get(pk=pk)
    data = GetMailBoxDetails(**select_as_dict(mail_box))
    return response_base.success(data=data)


@router.get(
    '',
    summary='（模糊条件）分页获取所有',
    dependencies=[
        DependsJwtAuth,
        DependsPagination,
    ],
)
async def get_pagination_mail_box(db: CurrentSession) -> ResponseModel:
    mail_box_select = await mail_box_service.get_select()
    page_data = await paging_data(db, mail_box_select, GetMailBoxListDetails)
    return response_base.success(data=page_data)


@router.post(
    '',
    summary='创建',
    dependencies=[
        Depends(RequestPermission(':add')),
        DependsRBAC,
    ],
)
async def create_mail_box(obj: CreateMailBoxParam) -> ResponseModel:
    await mail_box_service.create(obj=obj)
    return response_base.success()


@router.put(
    '/{pk}',
    summary='更新',
    dependencies=[
        Depends(RequestPermission(':edit')),
        DependsRBAC,
    ],
)
async def update_mail_box(pk: Annotated[int, Path(...)], obj: UpdateMailBoxParam) -> ResponseModel:
    count = await mail_box_service.update(pk=pk, obj=obj)
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
async def delete_mail_box(pk: Annotated[list[int], Query(...)]) -> ResponseModel:
    count = await mail_box_service.delete(pk=pk)
    if count > 0:
        return response_base.success()
    return response_base.fail()