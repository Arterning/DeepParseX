#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request

from backend.app.admin.schema.tag import CreateTagParam, GetTagListDetails, UpdateTagParam
from backend.app.admin.service.tag_service import tag_service
from backend.common.pagination import DependsPagination, paging_data
from backend.common.response.response_schema import ResponseModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db_pg import CurrentSession
from backend.utils.serializers import select_as_dict

router = APIRouter()


@router.get('/{pk}', summary='获取详情', dependencies=[DependsJwtAuth])
async def get_tag(pk: Annotated[int, Path(...)]) -> ResponseModel:
    tag = await tag_service.get(pk=pk)
    data = GetTagListDetails(**select_as_dict(tag))
    return response_base.success(data=data)


@router.get(
    '',
    summary='（模糊条件）分页获取所有',
    dependencies=[
        DependsJwtAuth,
        DependsPagination,
    ],
)
async def get_pagination_tag(db: CurrentSession) -> ResponseModel:
    tag_select = await tag_service.get_select()
    page_data = await paging_data(db, tag_select, GetTagListDetails)
    return response_base.success(data=page_data)


@router.post(
    '',
    summary='创建',
    dependencies=[
        Depends(RequestPermission(':add')),
        DependsRBAC,
    ],
)
async def create_tag(request: Request, obj: CreateTagParam) -> ResponseModel:
    obj.create_user = request.user.id
    await tag_service.create(obj=obj)
    return response_base.success()


@router.put(
    '/{pk}',
    summary='更新',
    dependencies=[
        Depends(RequestPermission(':edit')),
        DependsRBAC,
    ],
)
async def update_tag(pk: Annotated[int, Path(...)], obj: UpdateTagParam) -> ResponseModel:
    count = await tag_service.update(pk=pk, obj=obj)
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
async def delete_tag(pk: Annotated[list[int], Query(...)]) -> ResponseModel:
    count = await tag_service.delete(pk=pk)
    if count > 0:
        return response_base.success()
    return response_base.fail()