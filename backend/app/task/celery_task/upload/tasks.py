#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy.exc import SQLAlchemyError

from backend.app.admin.service.upload_service import upload_service
from backend.app.task.celery import celery_app
from backend.app.task.conf import task_settings
import time

@celery_app.task(
    name='upload_handle_file',
    bind=True,
    retry_backoff=True,
    max_retries=task_settings.CELERY_TASK_MAX_RETRIES,
)
async def upload_handle_file(self, **kwargs) -> int:
    """处理上传文件"""
    id = kwargs.get("id")
    if not id:
        raise ValueError("id is required")
    try:
        print("upload_handle_file")
        # await upload_service.handle_file(id=id)
        n = 30
        for i in range(0, n):
            self.update_state(state='PROGRESS', meta={'done': i, 'total': n})
            time.sleep(1)

        print("upload_handle_file ok")
    except SQLAlchemyError as exc:
        raise self.retry(exc=exc)
    result = {
        'status': 'success',
        'result': {
            'id': id,
            'message': '文件处理成功'
        }
    }
    return result
