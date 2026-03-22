#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from backend.app.admin.schema.geo_point import GetGeoPointListDetails
from backend.app.admin.service.geo_service import geo_service
from backend.common.pagination import DependsPagination, paging_data
from backend.common.response.response_schema import ResponseModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db_pg import CurrentSession

router = APIRouter()


@router.get(
    '',
    summary='分页获取地理坐标点列表',
    dependencies=[DependsJwtAuth, DependsPagination],
)
async def get_geo_list(
    db: CurrentSession,
    doc_id: Annotated[int | None, Query(description='按文档筛选')] = None,
    ioc_id: Annotated[int | None, Query(description='按IOC筛选')] = None,
    source_type: Annotated[str | None, Query(description='来源: exif / ip_ioc')] = None,
) -> ResponseModel:
    stmt = await geo_service.get_list(doc_id=doc_id, ioc_id=ioc_id, source_type=source_type)
    page_data = await paging_data(db, stmt, GetGeoPointListDetails)
    return response_base.success(data=page_data)


@router.get(
    '/map',
    summary='获取地图打点数据（含坐标的全量列表）',
    dependencies=[DependsJwtAuth],
)
async def get_map_points(
    source_type: Annotated[str | None, Query(description='来源过滤: exif / ip_ioc')] = None,
    doc_id: Annotated[int | None, Query(description='按文档过滤')] = None,
) -> ResponseModel:
    """返回所有有效坐标点，供前端地图组件直接渲染"""
    points = await geo_service.get_map_points(source_type=source_type, doc_id=doc_id)
    return response_base.success(data=points)


@router.delete(
    '',
    summary='（批量）删除地理坐标点',
    dependencies=[
        Depends(RequestPermission(':del')),
        DependsRBAC,
    ],
)
async def delete_geo_points(pk: Annotated[list[int], Query(...)]) -> ResponseModel:
    count = await geo_service.delete(pk=pk)
    if count > 0:
        return response_base.success()
    return response_base.fail()
