#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.app.admin.schema.person import CreatePersonParam, GetPersonDetails, GetPersonListDetails, UpdatePersonParam
from backend.app.admin.service.person_service import person_service
from backend.common.pagination import DependsPagination, paging_data
from backend.common.response.response_schema import ResponseModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db_pg import CurrentSession
from backend.utils.serializers import select_as_dict

router = APIRouter()


@router.get('/{pk}', summary='获取详情', dependencies=[DependsJwtAuth])
async def get_person(pk: Annotated[int, Path(...)]) -> ResponseModel:
    person = await person_service.get(pk=pk)
    data = GetPersonDetails(**select_as_dict(person))
    graph_data = await person_service.get_relation_graph_data(center_person_id=pk)
    data.graph_data = graph_data
    return response_base.success(data=data)


@router.get(
    '',
    summary='（模糊条件）分页获取所有',
    dependencies=[
        DependsJwtAuth,
        DependsPagination,
    ],
)
async def get_pagination_person(db: CurrentSession) -> ResponseModel:
    person_select = await person_service.get_select()
    page_data = await paging_data(db, person_select, GetPersonListDetails)
    return response_base.success(data=page_data)


@router.post(
    '',
    summary='创建',
    dependencies=[
        Depends(RequestPermission(':add')),
        DependsRBAC,
    ],
)
async def create_person(obj: CreatePersonParam) -> ResponseModel:
    await person_service.create(obj=obj)
    return response_base.success()


@router.put(
    '/{pk}',
    summary='更新',
    dependencies=[
        Depends(RequestPermission(':edit')),
        DependsRBAC,
    ],
)
async def update_person(pk: Annotated[int, Path(...)], obj: UpdatePersonParam) -> ResponseModel:
    count = await person_service.update(pk=pk, obj=obj)
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
async def delete_person(pk: Annotated[list[int], Query(...)]) -> ResponseModel:
    count = await person_service.delete(pk=pk)
    if count > 0:
        return response_base.success()
    return response_base.fail()