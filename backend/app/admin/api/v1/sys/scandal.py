#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional, Annotated

from fastapi import APIRouter, Query, Request
from sqlalchemy import select
from backend.utils.serializers import select_as_dict
from backend.app.admin.schema.scandal import CreateScandal, GetScandalList, UpdateScandal, GetScandalDetail
from backend.app.admin.service.scandal_service import scandal_service
from backend.common.response.response_schema import ResponseModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db_mysql import async_db_session
from backend.common.pagination import DependsPagination, paging_data
from backend.database.db_mysql import CurrentSession

router = APIRouter()


@router.post("", summary="创建黑料", dependencies=[DependsJwtAuth])
async def create_scandal(request: Request, obj: CreateScandal) -> ResponseModel:
    """创建黑料"""
    await scandal_service.create(obj=obj)
    return await response_base.success()


@router.put("/{pk}", summary="更新黑料", dependencies=[DependsJwtAuth])
async def update_scandal(request: Request, pk: int, obj: UpdateScandal) -> ResponseModel:
    """更新黑料"""
    count = await scandal_service.update(pk=pk, obj=obj)
    return await response_base.success(data={"count": count})


@router.delete("", summary="删除黑料", dependencies=[DependsJwtAuth])
async def delete_scandal(pk: Annotated[list[int], Query(...)]) -> ResponseModel:
    """删除黑料"""
    count = await scandal_service.delete(pk=pk)
    return await response_base.success(data={"count": count})


@router.get("/{pk}", summary="获取黑料详情", dependencies=[DependsJwtAuth])
async def get_scandal(request: Request, pk: int) -> ResponseModel:
    """获取黑料详情"""
    result = await scandal_service.get(pk=pk)
    data = GetScandalDetail(**await select_as_dict(result))
    return await response_base.success(data=data)


@router.get("", summary="获取黑料列表", dependencies=[DependsJwtAuth, DependsPagination])
async def get_scandals(
    db: CurrentSession,
    request: Request,
    name: Optional[str] = Query(None, description="标题"),
    person_id: Optional[int] = Query(None, description="人物"),
    content: Optional[str] = Query(None, description="黑料内容"),
) -> ResponseModel:
    """获取黑料列表"""
    se = await scandal_service.get_select(name=name, content=content)
    page_data = await paging_data(db, se, GetScandalList)
        
    return await response_base.success(data=page_data)
