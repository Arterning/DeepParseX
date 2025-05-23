#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.responses import StreamingResponse
from fastapi.exceptions import HTTPException

from backend.core.conf import settings
from backend.app.admin.schema.doc import CreateSysDocParam, GetSysDocListDetails, GetSysDocPage, UpdateSysDocParam, GetDocDetail
from backend.app.admin.service.doc_service import sys_doc_service
from backend.common.pagination import DependsPagination, paging_data
from backend.common.response.response_schema import ResponseModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db_pg import CurrentSession
from backend.utils.serializers import select_as_dict
from backend.utils.oss_client import minio_client

from minio.error import S3Error

router = APIRouter()


# 构建文件的知识图谱
@router.get('/build_graph/{pk}', summary='构建文件的知识图谱',
    dependencies=[DependsJwtAuth]
 )
async def build_graph(pk: Annotated[int, Path(...)]) -> ResponseModel:
    return await sys_doc_service.build_graph(pk=pk)


@router.get('/recent_docs/{pk}', summary='获取最新上传文件',
    dependencies=[DependsJwtAuth]
 )
async def get_recent_docs(request: Request) -> ResponseModel:
    user_id = request.user.id
    docs = await sys_doc_service.get_hot_docs(user_id)
    hot_docs = [GetSysDocListDetails(id=doc.id, title=doc.title, created_time=doc.created_time, updated_time=doc.updated_time) for doc in docs]
    return response_base.success(data=hot_docs)


bucket_name = settings.BUCKET_NAME

# 获取原文件
@router.get("/preview/{obj_name}", summary = "预览文件")
async def preview_pdf(obj_name: str):
    try:
        # 从 MinIO 获取对象
        response = minio_client.get_object(bucket_name, obj_name)

        # 获取文件的 MIME 类型
        media_type = response.getheader('Content-Type')
        
        async def file_generator(response):
            while True:
                chunk = response.read(9024)  # 逐块读取文件
                if not chunk:
                    break
                yield chunk
            response.close()
            response.release_conn()
        return StreamingResponse(file_generator(response), media_type=media_type)
    except S3Error as e:
        raise HTTPException(status_code=404, detail="File not found")



@router.get(
    '/search',
    summary='（模糊条件）获取所有文件',
    dependencies=[
        DependsJwtAuth,
        DependsPagination,
    ],
)
async def search(tokens: Annotated[str | None, Query()] = None) -> ResponseModel:
    docs = await sys_doc_service.search(tokens=tokens)
    return response_base.success(data=docs)


@router.get('/{pk}', summary='获取文件详情', dependencies=[DependsJwtAuth])
async def get_sys_doc(pk: Annotated[int, Path(...)]) -> ResponseModel:
    doc = await sys_doc_service.get(pk=pk)
    doc_data = []
    for data in doc.doc_data:
        doc_data.append(data.excel_data)
    data = GetDocDetail(id=doc.id, title=doc.title, name=doc.name, file=doc.file,
                        content=doc.content, created_time=doc.created_time,
                        updated_time=doc.updated_time, desc=doc.desc,
                        type=doc.type, doc_data=doc_data,account_pwd=doc.account_pwd)
    return response_base.success(data=data)


@router.get(
    '',
    summary='（模糊条件）分页获取所有文件',
    dependencies=[
        DependsJwtAuth,
        DependsPagination,
    ],
)
async def get_pagination_sys_doc(db: CurrentSession, 
                                 name: Annotated[str | None, Query()] = None,
                                 tokens: Annotated[str | None, Query()] = None,
                                 likeq: Annotated[str | None, Query()] = None,
                                 email_from: Annotated[str | None, Query()] = None,
                                 email_subject: Annotated[str | None, Query()] = None,
                                 email_time: Annotated[str | None, Query()] = None,
                                 email_to: Annotated[str | None, Query()] = None,
                                 type: Annotated[str | None, Query()] = None,) -> ResponseModel:
    # ids = await sys_doc_service.token_search(tokens=tokens)
    sys_doc_select = await sys_doc_service.get_select(name=name, type=type, tokens=tokens, likeq=likeq,
                                                      email_from=email_from, email_subject=email_subject,
                                                      email_time=email_time, email_to=email_to)
    page_data = await paging_data(db, sys_doc_select, GetSysDocPage)
    return response_base.success(data=page_data)


@router.post(
    '',
    summary='创建文件',
    dependencies=[
        Depends(RequestPermission('sys:doc:add')),
        DependsRBAC,
    ],
)
async def create_sys_doc(obj: CreateSysDocParam) -> ResponseModel:
    await sys_doc_service.create(obj=obj)
    return response_base.success()


@router.put(
    '/{pk}',
    summary='更新文件',
    dependencies=[
        Depends(RequestPermission('sys:doc:edit')),
        DependsRBAC,
    ],
)
async def update_sys_doc(pk: Annotated[int, Path(...)], obj: UpdateSysDocParam) -> ResponseModel:
    count = await sys_doc_service.update(pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete(
    '',
    summary='（批量）删除文件',
    dependencies=[
        Depends(RequestPermission('sys:doc:del')),
        DependsRBAC,
    ],
)
async def delete_sys_doc(pk: Annotated[list[int], Query(...)]) -> ResponseModel:
    count = await sys_doc_service.delete(pk=pk)
    if count > 0:
        # 删除doc_data表和doc_chunk表
        await sys_doc_service.delete_doc_data(doc_id=pk)
        await sys_doc_service.delete_doc_chunk(doc_id=pk)
        return response_base.success()
    return response_base.fail()
