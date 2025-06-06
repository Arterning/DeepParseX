#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path

from backend.app.task.service.task_service import task_service
from backend.common.response.response_schema import ResponseModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.common.log import log

router = APIRouter()


@router.get('', summary='获取所有可执行任务模块', dependencies=[DependsJwtAuth])
async def get_all_tasks() -> ResponseModel:
    tasks = task_service.get_list()
    return response_base.success(data=tasks)


@router.get('/current', summary='获取当前正在执行的任务', dependencies=[DependsJwtAuth])
async def get_current_task() -> ResponseModel:
    task = task_service.get()
    return response_base.success(data=task)


@router.get('/{uid}/status', summary='获取任务状态', dependencies=[DependsJwtAuth])
async def get_task_status(uid: Annotated[str, Path(description='任务ID')]) -> ResponseModel:
    status = task_service.get_status(uid)
    return response_base.success(data=status)


@router.get('/{uid}', summary='获取任务结果', dependencies=[DependsJwtAuth])
async def get_task_result(uid: Annotated[str, Path(description='任务ID')]) -> ResponseModel:
    task = task_service.get_result(uid)
    return response_base.success(data=task)


import time
import json
from fastapi.responses import StreamingResponse
from backend.common.log import log
# sse get task result
@router.get('/{uid}/sse', summary='获取任务结果')
async def get_task_result_sse(uid: Annotated[str, Path(description='任务ID')]) -> StreamingResponse:
    def generate():
        while True:
            task = task_service.get_result(uid)
            if task.successful() or task.failed():
                yield f'data: {json.dumps(task.info)}\n\n'
                break
            else:
                log.info(f'任务 {uid} 执行中, 当前进度: {task.info}')
                yield f'data: {json.dumps(task.info)}\n\n'
                time.sleep(1)
    return StreamingResponse(generate(), media_type='text/event-stream')


@router.post(
    '/{name}',
    summary='执行任务',
    dependencies=[
        Depends(RequestPermission('sys:task:run')),
        DependsRBAC,
    ],
)
async def run_task(
    name: Annotated[str, Path(description='任务名称')],
    args: Annotated[list | None, Body(description='任务函数位置参数')] = None,
    kwargs: Annotated[dict | None, Body(description='任务函数关键字参数')] = None,
) -> ResponseModel:
    task = task_service.run(name=name, args=args, kwargs=kwargs)
    # log.info(f'任务 {name} 执行成功, 任务ID: {task}')
    return response_base.success(data=str(task))
