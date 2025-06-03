#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy.exc import SQLAlchemyError

from backend.app.admin.schema.doc import  UpdateSysDocParam
from backend.app.admin.service.upload_service import upload_service
from backend.app.admin.service.doc_service import sys_doc_service
from backend.app.admin.service.doc_service import sys_doc_service
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
        # print("upload_handle_file")

        self.update_state(state='PROGRESS', meta={'stage': '准备文件内容', 'progress': 0})

        doc = await sys_doc_service.get(pk=id)

        self.update_state(state='PROGRESS', meta={'stage': '读取文件内容', 'progress': 1/4})

        await upload_service.read_file_content(doc=doc)

        self.update_state(state='PROGRESS', meta={'stage': '创建分词索引', 'progress': 2/4})

        await sys_doc_service.create_doc_tokens(id=doc.id)

        self.update_state(state='PROGRESS', meta={'stage': '创建文本向量', 'progress': 3/4})

        await upload_service.insert_text_embs(id=doc.id)
        
        # n = 30
        # for i in range(0, n):
        #     self.update_state(state='PROGRESS', meta={'done': i, 'total': n})
        #     time.sleep(1)

        # print("upload_handle_file ok")

        obj = UpdateSysDocParam(status=1)
        await sys_doc_service.update(pk=doc.id, obj=obj)
    except Exception as e:
        # raise self.retry(exc=exc)
        obj = UpdateSysDocParam(status=2, error_msg=str(e))
        await sys_doc_service.update(pk=doc.id, obj=obj)
        result = {
            'stage': '处理失败',
            'progress': 1,
            'error_msg': str(e),
        }
        return result
    
    result = {
        'stage': '处理完成',
        'progress': 1,
    }
    return result
