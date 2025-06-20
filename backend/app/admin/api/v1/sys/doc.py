#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.responses import StreamingResponse
from fastapi.exceptions import HTTPException

from backend.core.conf import settings
from backend.app.admin.schema.doc import CreateSysDocParam, CollectDocParam, GetSysDocListDetails, GetSysDocPage, UpdateSysDocParam, GetDocDetail
from backend.app.admin.service.doc_service import sys_doc_service
from backend.app.admin.service.upload_service import upload_service
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


# collect_doc 收藏文件
@router.post('/collect', summary='收藏文件',
    dependencies=[DependsJwtAuth]
)
async def collect_doc(request: Request, obj: CollectDocParam) -> ResponseModel:
    user_id = request.user.id
    doc = await sys_doc_service.get(pk=obj.doc_id)
    if not doc:
        return response_base.fail(message='文件不存在')
    
    # 检查是否已收藏
    # if await sys_doc_service.is_collected(user_id=user_id, doc_id=pk):
    #     return response_base.fail(message='已收藏该文件')
    
    # 收藏文件
    await sys_doc_service.collect_doc(collecton_id=obj.collection_id, doc_id=obj.doc_id)
    return response_base.success(data='收藏成功')


# 构建文件的知识图谱
@router.get('/build_graph/{pk}', summary='构建文件的知识图谱',
    dependencies=[DependsJwtAuth]
 )
async def build_graph(pk: Annotated[int, Path(...)]) -> ResponseModel:
    await sys_doc_service.build_graph(pk=pk)
    doc = await sys_doc_service.get(pk=pk)
    if not doc.doc_spos:
        return response_base.fail()
    triples = doc.doc_spos
    visualize_knowledge_graph = sys_doc_service.build_visualize_knowledge_graph(triples=triples)
    return response_base.success(data=visualize_knowledge_graph)


# 提取内容
@router.get('/extract_text/{pk}', summary='提取文本',
    dependencies=[DependsJwtAuth]
 )
async def extract_text(pk: Annotated[int, Path(...)]) -> ResponseModel:
    data = await upload_service.extract_text(pk=pk)
    return response_base.success(data=data)


@router.get('/recent_docs', summary='获取最新上传文件',
    dependencies=[DependsJwtAuth]
 )
async def get_recent_docs(request: Request) -> ResponseModel:
    user_id = request.user.id
    docs = await sys_doc_service.get_hot_docs(user_id)
    hot_docs = [GetSysDocListDetails(id=doc.id, title=doc.title, type=doc.type, created_time=doc.created_time, updated_time=doc.updated_time) for doc in docs]
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

        if media_type == 'application/msword':
            import tempfile
            import asyncio
            import os
            import subprocess

            try:
                # 创建临时文件
                with tempfile.NamedTemporaryFile(suffix=".doc", delete=False) as temp_doc:
                    
                    temp_doc.write(response.read())
                    temp_doc_path = temp_doc.name

            
                # 使用LibreOffice进行转换
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(
                    None, 
                    lambda: subprocess.run([
                        "libreoffice",
                        "--headless",
                        "--convert-to", "pdf",
                        "--outdir", os.path.dirname(temp_doc_path),
                        temp_doc_path
                    ], check=True)
                )

                temp_pdf_path = os.path.splitext(temp_doc_path)[0] + ".pdf"

                # 读取PDF文件并创建生成器
                def pdf_generator():
                    try:
                        
                        with open(temp_pdf_path, "rb") as f:
                            while True:
                                chunk = f.read(9024)
                                if not chunk:
                                    break
                                yield chunk
                    finally:
                        # 清理临时文件
                        if os.path.exists(temp_doc_path):
                            os.unlink(temp_doc_path)
                        if os.path.exists(temp_pdf_path):
                            os.unlink(temp_pdf_path)

                # 返回PDF流
                return StreamingResponse(
                    pdf_generator(),
                    media_type="application/pdf",
                )
            except Exception as e:
                # 确保资源被释放
                if 'response' in locals():
                    response.close()
                    response.release_conn()
                if 'temp_doc_path' in locals() and os.path.exists(temp_doc_path):
                    os.unlink(temp_doc_path)
                if 'temp_pdf_path' in locals() and os.path.exists(temp_pdf_path):
                    os.unlink(temp_pdf_path)
                raise e
        
        
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")



@router.get(
    '/search',
    summary='（模糊条件）获取所有文件',
    dependencies=[
        DependsJwtAuth,
        DependsPagination,
    ],
)
async def search(
    tokens: Annotated[str | None, Query()] = None,
    page: Annotated[int | None, Query()] = None,
    size: Annotated[int | None, Query()] = None
) -> ResponseModel:
    docs = await sys_doc_service.search(tokens=tokens, page=page, size=size)
    return response_base.success(data=docs)


@router.get(
    '/similar_search',
    summary='（模糊条件）获取所有文件',
    dependencies=[
        DependsJwtAuth,
        DependsPagination,
    ],
)
async def similar_search(
    query: Annotated[str | None, Query()] = None,
    page: Annotated[int | None, Query()] = None,
    size: Annotated[int | None, Query()] = None
) -> ResponseModel:
    data = await sys_doc_service.similar_search(query=query, page=page, size=size)
    return response_base.success(data=data)



@router.get('/{pk}', summary='获取文件详情', dependencies=[DependsJwtAuth])
async def get_sys_doc(pk: Annotated[int, Path(...)]) -> ResponseModel:
    doc = await sys_doc_service.get(pk=pk)
    doc_data = []
    for data in doc.doc_data:
        doc_data.append(data.excel_data)
    doc_dict = select_as_dict(doc)
    graph_data = sys_doc_service.build_visualize_knowledge_graph(triples=doc.doc_spos)

    doc_dict.update({"doc_data": doc_data})
    doc_dict.update({"graph_data": graph_data})
    data = GetDocDetail(**doc_dict)
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
                                 title: Annotated[str | None, Query()] = None,
                                 doc_type: Annotated[str | None, Query()] = None,
                                 content: Annotated[str | None, Query()] = None,
                                 source: Annotated[str | None, Query()] = None,
                                 rangeValue: Annotated[list[str] | None, Query()] = ['', ''],
                                ) -> ResponseModel:
    # ids = await sys_doc_service.token_search(tokens=tokens)
    sys_doc_select = await sys_doc_service.get_select(
        name=name,
        title=title,
        doc_type=doc_type,
        source=source,
        content=content, 
        rangeValue=rangeValue,
    )
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
    doc = await sys_doc_service.create(obj=obj)
    await sys_doc_service.create_doc_tokens(id=doc.id)
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
    await sys_doc_service.create_doc_tokens(id=pk)
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
    
    for id in pk:
        doc = await sys_doc_service.get(pk=id)
        if not doc:
            continue
        file = doc.file
        try:
            minio_client.remove_object(bucket_name, file)
        except S3Error:
            continue
    return response_base.fail()
