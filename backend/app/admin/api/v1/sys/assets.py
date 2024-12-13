#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from typing import Annotated
from backend.common.response.response_schema import ResponseModel, response_base
from backend.app.admin.service.assets_service import assets_service
from fastapi import APIRouter, Path, Query
from backend.common.log import log
from backend.common.pagination import DependsPagination, paging_data
from backend.app.admin.schema.assets import AssetsParam, GetAssetListDetails
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db_pg import CurrentSession

router = APIRouter()

@router.get('/{pk}', summary='获得资产详情', dependencies=[DependsJwtAuth])
async def get(pk: Annotated[int, Path(...)]) -> ResponseModel:
    asset = await assets_service.get(pk=pk)
    return response_base.success(data=asset)

@router.get('', summary='获得分页资产', dependencies=[DependsJwtAuth, DependsPagination])
async def get_assets(
    db: CurrentSession,
    assets_name: Annotated[str | None, Query()] = None,
) -> ResponseModel:
    res_select = await assets_service.get_select(assets_name=assets_name)
    page_data = await paging_data(db, res_select, GetAssetListDetails)
    return response_base.success(data=page_data)

@router.post('/add_asset', summary='增加资产', dependencies=[DependsJwtAuth])
async def add_asset(obj:AssetsParam) -> ResponseModel:
    await assets_service.create(obj=obj)
    return response_base.success()



@router.put('/{pk}',summary='更新资产',dependencies=[DependsJwtAuth])
async def update_asset(pk: Annotated[int, Path(...)], obj: AssetsParam) -> ResponseModel:
    count = await assets_service.update(pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()
    

@router.delete(path='/{pk}',summary='删除资产',dependencies=[DependsJwtAuth]
)
async def delete_asset(pk: Annotated[int, Path(...)]) -> ResponseModel:
    count = await assets_service.delete(pk=pk)
    if count > 0:
        return response_base.success()
    return response_base.fail()