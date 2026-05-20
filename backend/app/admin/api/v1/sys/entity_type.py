#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from backend.app.admin.schema.entity_type import (
    AnalyzeEntityNLParam,
    CreateEntityTypeParam,
    ExtractRelationsParam,
    GetEntityTypeDetails,
    GetEntityTypeListDetails,
    UpdateEntityTypeParam,
)
from backend.app.admin.service.entity_type_service import entity_type_service
from backend.common.pagination import DependsPagination, paging_data
from backend.common.response.response_schema import response_base, ResponseModel
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db_pg import CurrentSession

router = APIRouter()


@router.get('/{pk}', summary='获取实体类型详情', dependencies=[DependsJwtAuth])
async def get_entity_type(pk: int) -> ResponseModel:
    entity_type = await entity_type_service.get(pk=pk)
    data = GetEntityTypeDetails.model_validate(entity_type)
    return response_base.success(data=data)


@router.get('/{pk}/export', summary='导出实体类型下的所有实体', dependencies=[DependsJwtAuth])
async def export_entity_type_entities(
    pk: int,
    format: Annotated[str, Query(pattern='^(csv|parquet)$')] = 'csv',
):
    data, filename, media_type = await entity_type_service.export_entities(pk=pk, format=format)
    encoded_filename = quote(filename)
    return StreamingResponse(
        iter([data]),
        media_type=media_type,
        headers={'Content-Disposition': f"attachment; filename*=UTF-8''{encoded_filename}"},
    )


@router.post('/{pk}/lake', summary='将实体类型下的所有实体入湖（导出 Parquet 到 MinIO）', dependencies=[DependsJwtAuth])
async def lake_entity_type_entities(pk: int) -> ResponseModel:
    object_name = await entity_type_service.lake_entities(pk=pk)
    return response_base.success(data={'object_name': object_name})


@router.post('/{pk}/extract-relations', summary='根据用户需求通过 AI 分析 Parquet 数据提取实体关系', dependencies=[DependsJwtAuth])
async def extract_relations(pk: int, obj: ExtractRelationsParam) -> ResponseModel:
    result = await entity_type_service.extract_relations(pk=pk, requirement=obj.requirement)
    return response_base.success(data=result)


@router.post('/analyze-nl', summary='通过自然语言分析实体数据（AI自动选择实体类型并生成SQL）', dependencies=[DependsJwtAuth])
async def analyze_entity_nl(obj: AnalyzeEntityNLParam) -> ResponseModel:
    result = await entity_type_service.analyze_entity_nl(question=obj.question)
    return response_base.success(data=result)


@router.get('', summary='分页获取实体类型列表', dependencies=[DependsJwtAuth, DependsPagination])
async def get_pagination_entity_types(
    db: CurrentSession,
    name: Annotated[str | None, Query()] = None,
) -> ResponseModel:
    entity_type_select = await entity_type_service.get_select(name=name)
    page_data = await paging_data(db, entity_type_select, GetEntityTypeListDetails)
    return response_base.success(data=page_data)


@router.post('', summary='创建实体类型', dependencies=[Depends(RequestPermission('sys:entity_type:add')), DependsRBAC])
async def create_entity_type(obj: CreateEntityTypeParam) -> ResponseModel:
    await entity_type_service.create(obj=obj)
    return response_base.success()


@router.put('/{pk}', summary='更新实体类型', dependencies=[Depends(RequestPermission('sys:entity_type:edit')), DependsRBAC])
async def update_entity_type(pk: int, obj: UpdateEntityTypeParam) -> ResponseModel:
    count = await entity_type_service.update(pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete(
    '', summary='批量删除实体类型', dependencies=[Depends(RequestPermission('sys:entity_type:del')), DependsRBAC]
)
async def delete_entity_type(pk: Annotated[list[int], Query(...)]) -> ResponseModel:
    count = await entity_type_service.delete(pk=pk)
    if count > 0:
        return response_base.success()
    return response_base.fail()
