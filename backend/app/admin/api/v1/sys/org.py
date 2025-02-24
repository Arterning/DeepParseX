#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from typing import Annotated
from backend.app.admin.schema.chat import ChatParam
from backend.common.response.response_schema import ResponseModel, response_base
from backend.common.pagination import DependsPagination, paging_data
from backend.app.admin.service.org_service import org_service
from fastapi import APIRouter, Path, Query
from backend.common.log import log
from backend.app.admin.schema.org import OrgParam, GetOrgListDetails, GetOrgDetail
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db_pg import CurrentSession

router = APIRouter()

@router.get('/{pk}', summary='获得组织详情', dependencies=[DependsJwtAuth])
async def get_orgs(pk: Annotated[int, Path(...)]) -> ResponseModel:
    org = await org_service.get(pk=pk)
    docs = [dict(id=doc.id, title=doc.title) for doc in org.docs]
    assets = [dict(id=a.id, title=a.assets_name) for a in org.assets]
    data = GetOrgDetail(id=org.id,org_name=org.org_name,org_assets_nums=org.org_assets_nums,
                        org_file_nums=org.org_file_nums,org_desc=org.org_desc,
                          docs=docs, assets=assets)
    return response_base.success(data=data)

@router.get('', summary='获得分页组织', dependencies=[DependsJwtAuth, DependsPagination])
async def get_org(
    db: CurrentSession,
    name: Annotated[str | None, Query()] = None,
) -> ResponseModel:
    org_select = await org_service.get_select(name=name)
    page_data = await paging_data(db, org_select, GetOrgListDetails)
    return response_base.success(data=page_data)

@router.post('/add_org', summary='增加组织', dependencies=[DependsJwtAuth])
async def add_org(obj:OrgParam) -> ResponseModel:
    await org_service.create(obj=obj)
    return response_base.success()


@router.put('/{pk}',summary='更新组织',dependencies=[DependsJwtAuth])
async def update_org(pk: Annotated[int, Path(...)], obj: OrgParam) -> ResponseModel:
    count = await org_service.update(pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()
    

@router.delete(path='',summary='（批量）删除组织',dependencies=[DependsJwtAuth])
async def delete_org(pk: Annotated[list[int], Query(...)]) -> ResponseModel:
    count = await org_service.delete(pk=pk)
    if count > 0:
        return response_base.success()
    return response_base.fail()