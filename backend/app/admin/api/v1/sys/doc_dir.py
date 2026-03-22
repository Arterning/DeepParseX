#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.app.admin.schema.doc_dir import CreateDocDirParam, GetDocDirListDetails, UpdateDocDirParam
from backend.app.admin.service.doc_dir_service import doc_dir_service
from backend.common.response.response_schema import ResponseModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.utils.serializers import select_as_dict, select_columns_serialize

router = APIRouter()


@router.get('/{pk}', summary='获取目录详情', dependencies=[DependsJwtAuth])
async def get_doc_dir(pk: Annotated[int, Path(...)]) -> ResponseModel:
    doc_dir = await doc_dir_service.get_with_children(pk=pk)
    # select_columns_serialize 只读表列字段，不含关联属性，避免 children 重复传入或触发懒加载
    children = [
        GetDocDirListDetails(**select_columns_serialize(child), children=[])
        for child in (doc_dir.children or [])
    ]
    data = GetDocDirListDetails(**select_columns_serialize(doc_dir), children=children)
    return response_base.success(data=data)


@router.get('', summary='获取所有目录展示树', dependencies=[DependsJwtAuth])
async def get_all_doc_dirs_tree(
    name: Annotated[str | None, Query()] = None,
) -> ResponseModel:
    doc_dirs = await doc_dir_service.get_doc_dir_tree(name=name)
    return response_base.success(data=doc_dirs)


@router.post(
    '',
    summary='创建目录',
    dependencies=[
        Depends(RequestPermission('sys:doc_dir:add')),
        DependsRBAC,
    ],
)
async def create_doc_dir(obj: CreateDocDirParam) -> ResponseModel:
    await doc_dir_service.create(obj=obj)
    return response_base.success()


@router.put(
    '/{pk}',
    summary='更新目录',
    dependencies=[
        Depends(RequestPermission('sys:doc_dir:edit')),
        DependsRBAC,
    ],
)
async def update_doc_dir(pk: Annotated[int, Path(...)], obj: UpdateDocDirParam) -> ResponseModel:
    count = await doc_dir_service.update(pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete(
    '/{pk}',
    summary='删除目录',
    dependencies=[
        Depends(RequestPermission('sys:doc_dir:del')),
        DependsRBAC,
    ],
)
async def delete_doc_dir(pk: Annotated[int, Path(...)]) -> ResponseModel:
    count = await doc_dir_service.delete(pk=pk)
    if count > 0:
        return response_base.success()
    return response_base.fail()
