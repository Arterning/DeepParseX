#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.app.admin.schema.news import CreateNewsParam, GetNewsListDetails, UpdateNewsParam
from backend.app.admin.service.news_service import news_service
from backend.common.pagination import DependsPagination, paging_data
from backend.common.response.response_schema import ResponseModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db_pg import CurrentSession

router = APIRouter()


@router.get('/{pk}', summary='获取详情', dependencies=[DependsJwtAuth])
async def get_news(pk: Annotated[int, Path(...)]) -> ResponseModel:
    news = await news_service.get(pk=pk)
    return response_base.success(data=news)


@router.get(
    '',
    summary='（模糊条件）分页获取所有',
    dependencies=[
        DependsJwtAuth,
        DependsPagination,
    ],
)
async def get_pagination_news(db: CurrentSession) -> ResponseModel:
    news_select = await news_service.get_select()
    page_data = await paging_data(db, news_select, GetNewsListDetails)
    return response_base.success(data=page_data)


@router.post(
    '',
    summary='创建',
    dependencies=[
        Depends(RequestPermission(':add')),
        DependsRBAC,
    ],
)
async def create_news(obj: CreateNewsParam) -> ResponseModel:
    await news_service.create(obj=obj)
    return response_base.success()


@router.put(
    '/{pk}',
    summary='更新',
    dependencies=[
        Depends(RequestPermission(':edit')),
        DependsRBAC,
    ],
)
async def update_news(pk: Annotated[int, Path(...)], obj: UpdateNewsParam) -> ResponseModel:
    count = await news_service.update(pk=pk, obj=obj)
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
async def delete_news(pk: Annotated[list[int], Query(...)]) -> ResponseModel:
    count = await news_service.delete(pk=pk)
    if count > 0:
        return response_base.success()
    return response_base.fail()