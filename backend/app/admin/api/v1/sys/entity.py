#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.app.admin.schema.entity import CreateEntityParam, GetEntityDetails, GetEntityListDetails, UpdateEntityParam
from backend.app.admin.service.entity_service import entity_service
from backend.common.pagination import DependsPagination, paging_data
from backend.common.response.response_schema import ResponseModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db_pg import CurrentSession
from backend.utils.serializers import select_as_dict

router = APIRouter()


@router.get('/{pk}', summary='获取详情', dependencies=[DependsJwtAuth])
async def get_entity(pk: Annotated[int, Path(...)]) -> ResponseModel:
    entity = await entity_service.get(pk=pk)
    # 获取实体的关系数据
    relationships = await entity_service.get_entity_relationships(entity_id=pk)
    # 构建返回数据
    data = GetEntityDetails(**select_as_dict(entity), relationships=relationships)
    return response_base.success(data=data)


@router.get(
    '',
    summary='（模糊条件）分页获取所有',
    dependencies=[
        DependsJwtAuth,
        DependsPagination,
    ],
)
async def get_pagination_entity(
    db: CurrentSession,
    name: Annotated[str | None, Query(title='实体名称', description='模糊匹配')] = None,
    entity_type: Annotated[list[str] | None, Query(title='实体类型', description='支持多个实体类型，格式为数组')] = None,
) -> ResponseModel:
    entity_select = await entity_service.get_select(name=name, entity_type=entity_type)
    page_data = await paging_data(db, entity_select, GetEntityListDetails)
    return response_base.success(data=page_data)


@router.post(
    '',
    summary='创建',
    dependencies=[
        Depends(RequestPermission(':add')),
        DependsRBAC,
    ],
)
async def create_entity(obj: CreateEntityParam) -> ResponseModel:
    await entity_service.create(obj=obj)
    return response_base.success()


@router.put(
    '/{pk}',
    summary='更新',
    dependencies=[
        Depends(RequestPermission(':edit')),
        DependsRBAC,
    ],
)
async def update_entity(pk: Annotated[int, Path(...)], obj: UpdateEntityParam) -> ResponseModel:
    count = await entity_service.update(pk=pk, obj=obj)
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
async def delete_entity(pk: Annotated[list[int], Query(...)]) -> ResponseModel:
    count = await entity_service.delete(pk=pk)
    if count > 0:
        return response_base.success()
    return response_base.fail()