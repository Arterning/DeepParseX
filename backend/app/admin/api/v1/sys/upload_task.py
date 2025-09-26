#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.app.admin.schema.upload_task import CreateUploadTaskParam, GetUploadTaskDetails, GetUploadTaskListDetails, UpdateUploadTaskParam
from backend.app.admin.service.upload_task_service import upload_task_service
from backend.common.pagination import DependsPagination, paging_data
from backend.common.response.response_schema import ResponseModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db_pg import CurrentSession
from backend.utils.serializers import select_as_dict

router = APIRouter()


@router.get('/{pk}', summary='获取详情', dependencies=[DependsJwtAuth])
async def get_upload_task(pk: Annotated[int, Path(...)]) -> ResponseModel:
    upload_task = await upload_task_service.get(pk=pk)
    data = GetUploadTaskListDetails(**select_as_dict(upload_task))
    return response_base.success(data=data)


@router.get(
    '',
    summary='（模糊条件）分页获取所有',
    dependencies=[
        DependsJwtAuth,
        DependsPagination,
    ],
)
async def get_pagination_upload_task(
    db: CurrentSession,
    name: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
    source: Annotated[str | None, Query()] = None,
    rangeValue: Annotated[list[str] | None, Query()] = ['', ''],
) -> ResponseModel:
    upload_task_select = await upload_task_service.get_select(name=name, status=status, source=source, rangeValue=rangeValue)
    page_data = await paging_data(db, upload_task_select, GetUploadTaskListDetails)
    return response_base.success(data=page_data)


@router.post(
    '',
    summary='创建',
    dependencies=[
        Depends(RequestPermission(':add')),
        DependsRBAC,
    ],
)
async def create_upload_task(obj: CreateUploadTaskParam) -> ResponseModel:
    await upload_task_service.create(obj=obj)
    return response_base.success()


@router.put(
    '/{pk}',
    summary='更新',
    dependencies=[
        Depends(RequestPermission(':edit')),
        DependsRBAC,
    ],
)
async def update_upload_task(pk: Annotated[int, Path(...)], obj: UpdateUploadTaskParam) -> ResponseModel:
    count = await upload_task_service.update(pk=pk, obj=obj)
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
async def delete_upload_task(pk: Annotated[list[int], Query(...)]) -> ResponseModel:
    count = await upload_task_service.delete(pk=pk)
    if count > 0:
        return response_base.success()
    return response_base.fail()