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
from backend.database.db_pg import CurrentSession
from backend.utils.serializers import select_as_dict

router = APIRouter()


@router.get('/all', summary='获取用户所有标签', dependencies=[DependsJwtAuth])
async def get_all_user_tags(
    request: Request,
    tag_type: Annotated[str | None, Query(description='标签类型过滤，如 mail_box')] = None,
) -> ResponseModel:
    """获取当前用户的所有标签（包括用户创建的标签和系统标签），可按类型过滤"""
    user_id = request.user.id
    tags = await tag_service.get_all_by_user(user_id=user_id, tag_type=tag_type)
    data = [GetTagListDetails(**select_as_dict(tag)) for tag in tags]
    return response_base.success(data=data)


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
        DependsJwtAuth,
    ],
)
async def create_tag(request: Request, obj: CreateTagParam) -> ResponseModel:
    obj.create_user = request.user.id
    tag = await tag_service.create(obj=obj)
    data = GetTagListDetails(**select_as_dict(tag))
    return response_base.success(data=data)


@router.put(
    '/{pk}',
    summary='更新',
    dependencies=[
        DependsJwtAuth,
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
        DependsJwtAuth,
    ],
)
async def delete_tag(pk: Annotated[list[int], Query(...)]) -> ResponseModel:
    count = await tag_service.delete(pk=pk)
    if count > 0:
        return response_base.success()
    return response_base.fail()