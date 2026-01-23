#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
from fastapi import APIRouter, Path, BackgroundTasks
from datetime import datetime
from typing import Annotated, Optional
from pydantic import BaseModel
from backend.common.response.response_schema import response_base
from backend.app.admin.service.upload_service import upload_service
from backend.app.admin.service.doc_service import sys_doc_service
from backend.app.admin.service.upload_task_service import upload_task_service
from backend.app.admin.schema.upload_task import CreateUploadTaskParam, UpdateUploadTaskParam
from backend.app.admin.model.sys_upload_task import UploadTask
from backend.app.admin.model.sys_doc import SysDoc
from backend.database.db_pg import async_db_session
from sqlalchemy import select, update
import time
import json
from fastapi.responses import StreamingResponse
from fastapi import File, UploadFile, Form, Request
from backend.common.log import log
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db_redis import redis_client
import os


# 定义接收JSON参数的模型
class ParseParams(BaseModel):
    name: Optional[str] = None
    doc_dir_id: Optional[int] = None
    option: Optional[dict] = None

router = APIRouter()

def _count_compressed_files_sync(bucket_name: str, file_path: str, file_suffix: str) -> int:
    """同步函数：获取并解析压缩包文件数量"""
    from backend.utils.upload_utils import is_zip_file, is_rar_file, is_7z_file
    from backend.utils.oss_client import minio_client
    import io
    import zipfile
    import rarfile

    response = minio_client.get_object(bucket_name, file_path)
    file_bytes = response.read()

    if is_zip_file(file_suffix):
        zip_buffer = io.BytesIO(file_bytes)
        with zipfile.ZipFile(zip_buffer, 'r') as zip_ref:
            valid_files = [f for f in zip_ref.infolist() if not f.is_dir() and not f.filename.startswith('__MACOSX')]
            return len(valid_files)
    elif is_rar_file(file_suffix):
        rar_buffer = io.BytesIO(file_bytes)
        with rarfile.RarFile(rar_buffer, 'r') as rar_ref:
            valid_files = [f for f in rar_ref.infolist() if not f.is_dir() and not f.filename.startswith('__MACOSX')]
            return len(valid_files)
    elif is_7z_file(file_suffix):
        return 1
    return 1


async def get_compressed_file_count(doc_id: int) -> int:
    """获取压缩包中的文件数量"""
    from backend.app.admin.service.doc_service import sys_doc_service
    from backend.utils.upload_utils import get_file_suffix, is_zip_file, is_rar_file, is_7z_file
    from backend.core.conf import settings

    # 首先获取文档信息
    doc = await sys_doc_service.get(pk=doc_id)
    file_suffix = get_file_suffix(doc.file)

    # 非压缩包文件返回1
    if not (is_zip_file(file_suffix) or is_rar_file(file_suffix) or is_7z_file(file_suffix)):
        return 1

    # 在线程池中执行同步的压缩包读取操作
    try:
        bucket_name = settings.BUCKET_NAME
        count = await asyncio.to_thread(
            _count_compressed_files_sync, bucket_name, doc.file, file_suffix
        )
        return count
    except Exception as e:
        log.error(f"读取压缩包文件数量失败: {e}")
        import traceback
        traceback.print_exc()

    # 出现异常时返回默认值1
    return 1


@router.post("/", summary='上传文件', dependencies=[DependsJwtAuth])
async def upload_file(
    file: UploadFile = File(...), 
    last_modified: Annotated[datetime| None, Form(...)] = None,
    size: Annotated[int | None, Form(...)] = None,
    request: Request = None,
):
    meta = {
        "last_modified": last_modified,
        "size": size,
    }
    # print("meta", meta)
    # print("request", request.user)
    user = request.user
    doc = await upload_service.save_file(file, meta, user)
    resp = {
        "id": doc.id
    }
    return response_base.success(data=resp)


@router.post("/parse/{pk}", summary='解析文件', dependencies=[DependsJwtAuth])
async def parse(
    pk: Annotated[int, Path(...)],
    background_tasks: BackgroundTasks,
    request: Request, 
    params: ParseParams
):
    name = params.name
    doc_dir_id = params.doc_dir_id
    option = params.option
    source = f"({request.user.dept.name}){request.user.username}"
    
    # 获取文件数量，对于压缩包文件会读取实际包含的文件数量
    file_count = await get_compressed_file_count(pk)
    
    # 创建上传任务
    task_obj = CreateUploadTaskParam(
        name=name,
        status='pending',
        doc_id=pk,
        doc_dir_id=doc_dir_id,
        option=option,
        source=source,
        create_user=request.user.id,
        file_count=file_count
    )
    task = await upload_task_service.create(obj=task_obj)
    # 更新文档的upload_task_id
    await sys_doc_service.base_update(pk=pk, obj={
        'upload_task_id': task.id,
        'doc_dir_id': doc_dir_id,
    })
    
    background_tasks.add_task(run_parse_task, pk=pk)
    return response_base.success(data="任务已提交，正在处理")


async def run_parse_task(pk: int):

    redis_key = f'parse-document-stage:{pk}'

    await redis_client.set(
            redis_key, json.dumps({
                'status': 'doing',
                'stage': '识别文件', 
                'progress': 1/5
            }), 
            ex = 60 * 5
        )

    doc = await sys_doc_service.get(pk=pk)

    try:
        
        await redis_client.set(
            redis_key, json.dumps({
                'status': 'doing',
                'stage': '读取内容', 
                'progress': 2/5
            }), 
            ex = 60 * 5
        )

        await upload_service.read_file_content(doc=doc)

        sub_docs = []

        # 处理压缩包中的文件
        async with async_db_session() as db:
            # 查询所有belong等于当前文档ID的文件
            stmt = select(SysDoc).where(SysDoc.belong == doc.id)
            result = await db.execute(stmt)
            sub_docs = result.scalars().all()


        for sub_doc in sub_docs:
            await upload_service.read_file_content(doc=sub_doc)

            await redis_client.set(
                redis_key, json.dumps({
                    'status': 'doing',
                    'stage': f'读取内容-({sub_doc.name})', 
                    'progress': 2/5
                }), 
                ex = 60 * 5
            )


        await redis_client.set(
            redis_key, json.dumps({
                'status': 'doing',
                'stage': '创建索引', 
                'progress': 3/5
            }), 
            ex = 60 * 5
        )

        await sys_doc_service.create_doc_tokens(id=doc.id)

        for sub_doc in sub_docs:
            await redis_client.set(
                redis_key, json.dumps({
                    'status': 'doing',
                    'stage': f'创建索引-({sub_doc.name})', 
                    'progress': 3/5
                }), 
                ex = 60 * 5
            )
            await sys_doc_service.create_doc_tokens(id=sub_doc.id)
        
        
        await redis_client.set(
            redis_key, json.dumps({
                'status': 'doing',
                'stage': '更新状态', 
                'progress': 4/5
            }), 
            ex = 60 * 5
        )

        await sys_doc_service.base_update(pk=doc.id, obj={
            'status': 1,
        })

        # 更新belong等于当前文档ID的文件状态为已解析
        async with async_db_session.begin() as db:
            stmt = update(SysDoc).where(SysDoc.belong == doc.id).values(status=1)
            await db.execute(stmt)
            await db.commit()


        async with async_db_session() as db:
            stmt = select(UploadTask).where(UploadTask.doc_id == doc.id)
            result = await db.execute(stmt)
            task = result.scalar_one_or_none()
            if task:
                await upload_task_service.update(pk=task.id, obj=UpdateUploadTaskParam(name=task.name, status='done'))

        await redis_client.set(
            redis_key, json.dumps({
                'status': 'done',
                'stage': '处理完成', 
                'progress': 1
            }), 
            ex = 60 * 5
        )
    except Exception as e:
        log.error(e)
        import traceback
        traceback.print_exc()  # 打印完整的堆栈跟踪信息
        async with async_db_session() as db:
            stmt = select(UploadTask).where(UploadTask.option['doc_id'].astext == str(doc.id))
            result = await db.execute(stmt)
            task = result.scalar_one_or_none()
            if task:
                await upload_task_service.update(pk=task.id, obj=UpdateUploadTaskParam(name=task.name, status='error'))
        await redis_client.set(
            redis_key, json.dumps({
                'status': 'error',
                'stage': '处理失败', 
                'progress': 0
            }), 
            ex = 60 * 5
        )
        await sys_doc_service.base_update(pk=doc.id, obj={
            'status': 2,
            'error_msg': str(e)
        })
    return response_base.success(data="OK")


@router.get('/sse/{pk}', summary='获取任务结果')
async def get_upload_sse(pk: Annotated[str, Path(description='文件ID')]) -> StreamingResponse:
    
    redis_key = f'parse-document-stage:{pk}'

    async def generate():
        
        while True:
            result = await redis_client.get(redis_key)
            result_json = {}
            if result:
                result_json = json.loads(result)
            if result_json and result_json.get('status') != 'doing':
                yield f'data: {result}\n\n'
                break
            else:
                yield f'data: {result}\n\n'
                await asyncio.sleep(1)
    return StreamingResponse(generate(), media_type='text/event-stream')
