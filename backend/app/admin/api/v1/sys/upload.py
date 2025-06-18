#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
from fastapi import APIRouter, Path, BackgroundTasks
from datetime import datetime
from typing import Annotated
from backend.common.response.response_schema import response_base
from backend.app.admin.service.upload_service import upload_service
from backend.app.admin.service.doc_service import sys_doc_service
import time
import json
from fastapi.responses import StreamingResponse
from fastapi import File, UploadFile, Form, Request
from backend.common.log import log
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db_redis import redis_client
import os

router = APIRouter()


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
    background_tasks: BackgroundTasks
):
    
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

        await redis_client.set(
            redis_key, json.dumps({
                'status': 'doing',
                'stage': '创建索引', 
                'progress': 3/5
            }), 
            ex = 60 * 5
        )
        
        await sys_doc_service.create_doc_tokens(id=doc.id)

        
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

        await redis_client.set(
            redis_key, json.dumps({
                'status': 'done',
                'stage': '处理完成', 
                'progress': 1
            }), 
            ex = 60 * 5
        )
    except Exception as e:
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
