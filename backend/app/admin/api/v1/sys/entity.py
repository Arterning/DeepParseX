#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, Request

from backend.app.admin.schema.entity import AnalyzeEntitiesParam, CreateEntityParam, GetEntityDetails, GetEntityListDetails, UpdateEntityParam
from backend.app.admin.service.entity_service import entity_service
from backend.common.pagination import DependsPagination, paging_data
from backend.common.response.response_schema import ResponseModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db_pg import CurrentSession
from backend.utils.serializers import select_as_dict

router = APIRouter()


@router.post(
    '/analyze',
    summary='分析实体关系图谱',
    dependencies=[DependsJwtAuth],
)
async def analyze_entities(obj: AnalyzeEntitiesParam) -> ResponseModel:
    """
    分析多个实体之间的关系，返回图谱数据（nodes + edges）
    """
    data = await entity_service.analyze_entities(entity_ids=obj.entity_ids)
    return response_base.success(data=data)


@router.get('/{pk}', summary='获取详情', dependencies=[DependsJwtAuth])
async def get_entity(pk: Annotated[int, Path(...)]) -> ResponseModel:
    entity = await entity_service.get(pk=pk)
    # 获取实体的关系数据
    relationships = await entity_service.get_entity_relationships(entity_id=pk)
    # 获取实体的收藏状态
    starred_ids = await entity_service.get_starred_ids(entity_id=pk)
    # 构建返回数据
    data = GetEntityDetails(**select_as_dict(entity), relationships=relationships, starred_ids=starred_ids)
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
    mail: Annotated[bool | None, Query(title='是否仅显示关联邮件的实体', description='仅当true时筛选，false/空均不筛选')] = None,
) -> ResponseModel:
    entity_select = await entity_service.get_select(name=name, entity_type=entity_type, eml=mail)
    page_data = await paging_data(db, entity_select, GetEntityListDetails)
    return response_base.success(data=page_data)


@router.post(
    '',
    summary='创建',
    dependencies=[
        DependsJwtAuth,
    ],
)
async def create_entity(obj: CreateEntityParam) -> ResponseModel:
    await entity_service.create(obj=obj)
    return response_base.success()


@router.put(
    '/{pk}',
    summary='更新',
    dependencies=[
        DependsJwtAuth,
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


@router.post(
    '/{pk}/generate-properties',
    summary='AI生成实体属性',
    dependencies=[DependsJwtAuth],
)
async def generate_entity_properties(pk: Annotated[int, Path(...)]) -> ResponseModel:
    """
    根据实体类型调用AI生成实体属性

    目前支持的实体类型：
    - 人物：生成性别、国籍、组织、职位、联系方式等属性
    """
    properties = await entity_service.generate_properties_by_ai(pk=pk)
    return response_base.success(data=properties)


@router.post(
    '/{pk}/star',
    summary='收藏实体到收藏夹',
    dependencies=[DependsJwtAuth],
)
async def star_entity(
    request: Request,
    pk: Annotated[int, Path(..., description='实体ID')],
    star_id: Annotated[int, Body(..., embed=True, description='收藏夹ID')],
) -> ResponseModel:
    """
    将实体添加到指定收藏夹
    """
    user_id = request.user.id
    added = await entity_service.add_to_star(entity_id=pk, star_id=star_id, created_by=user_id)
    if added:
        return response_base.success()
    return response_base.fail()


@router.delete(
    '/{pk}/star',
    summary='取消收藏实体',
    dependencies=[DependsJwtAuth],
)
async def unstar_entity(
    pk: Annotated[int, Path(..., description='实体ID')],
    star_id: Annotated[int, Query(..., description='收藏夹ID')],
) -> ResponseModel:
    """
    从指定收藏夹移除实体
    """
    removed = await entity_service.remove_from_star(entity_id=pk, star_id=star_id)
    if removed:
        return response_base.success()
    return response_base.fail()