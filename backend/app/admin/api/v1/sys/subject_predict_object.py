#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.app.admin.schema.subject_predict_object import CreateSubjectPredictObjectParam, GetSubjectPredictObjectDetails, GetSubjectPredictObjectListDetails, UpdateSubjectPredictObjectParam
from backend.app.admin.service.subject_predict_object_service import sys_subject_predict_object_service
from backend.common.pagination import DependsPagination, paging_data
from backend.common.response.response_schema import ResponseModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.database.db_pg import CurrentSession
from backend.utils.serializers import select_as_dict

router = APIRouter()


@router.get('/{pk}', summary='获取详情', dependencies=[DependsJwtAuth])
async def get_sys_subject_predict_object(pk: Annotated[int, Path(...)]) -> ResponseModel:
    sys_subject_predict_object = await sys_subject_predict_object_service.get(pk=pk)
    data = GetSubjectPredictObjectListDetails(**select_as_dict(sys_subject_predict_object))
    return response_base.success(data=data)


@router.get(
    '',
    summary='（模糊条件）分页获取所有',
    dependencies=[
        DependsJwtAuth,
        DependsPagination,
    ],
)
async def get_pagination_sys_subject_predict_object(db: CurrentSession) -> ResponseModel:
    sys_subject_predict_object_select = await sys_subject_predict_object_service.get_select()
    page_data = await paging_data(db, sys_subject_predict_object_select, GetSubjectPredictObjectListDetails)
    return response_base.success(data=page_data)


@router.post(
    '',
    summary='创建',
    dependencies=[
        DependsJwtAuth,
    ],
)
async def create_sys_subject_predict_object(obj: CreateSubjectPredictObjectParam) -> ResponseModel:
    await sys_subject_predict_object_service.create(obj=obj)
    return response_base.success()


@router.put(
    '/{pk}',
    summary='更新',
    dependencies=[
        DependsJwtAuth,
    ],
)
async def update_sys_subject_predict_object(pk: Annotated[int, Path(...)], obj: UpdateSubjectPredictObjectParam) -> ResponseModel:
    count = await sys_subject_predict_object_service.update(pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete(
    '',
    summary='（批量）删除',
    dependencies=[
        DependsJwtAuth,
    ],
)
async def delete_sys_subject_predict_object(pk: Annotated[list[int], Query(...)]) -> ResponseModel:
    count = await sys_subject_predict_object_service.delete(pk=pk)
    if count > 0:
        return response_base.success()
    return response_base.fail()