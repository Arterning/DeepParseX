#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from backend.app.admin.crud.crud_upload_task import upload_task_dao
from backend.app.admin.model.sys_upload_task import UploadTask
from backend.app.admin.schema.upload_task import CreateUploadTaskParam, UpdateUploadTaskParam
from backend.common.exception import errors
from backend.database.db_pg import async_db_session
from sqlalchemy import Select


class UploadTaskService:
    @staticmethod
    async def get(*, pk: int) -> UploadTask:
        async with async_db_session() as db:
            upload_task = await upload_task_dao.get(db, pk)
            if not upload_task:
                raise errors.NotFoundError(msg='不存在')
            return upload_task
    
    @staticmethod
    async def get_select(name: str | None = None, status: str | None = None, source: str | None = None, rangeValue: list[str] | None = None, create_user: int | None = None) -> Select:
        return await upload_task_dao.get_list(name=name, status=status, source=source, rangeValue=rangeValue, create_user=create_user)

    @staticmethod
    async def get_all() -> Sequence[UploadTask]:
        async with async_db_session() as db:
            upload_tasks = await upload_task_dao.get_all(db)
            return upload_tasks

    @staticmethod
    async def create(*, obj: CreateUploadTaskParam) -> UploadTask:
        async with async_db_session.begin() as db:
            return await upload_task_dao.create(db, obj)

    @staticmethod
    async def update(*, pk: int, obj: UpdateUploadTaskParam) -> int:
        async with async_db_session.begin() as db:
            count = await upload_task_dao.update(db, pk, obj)
            return count

    @staticmethod
    async def update_status_by_doc_id(*, doc_id: int, status: str) -> int:
        async with async_db_session.begin() as db:
            return await upload_task_dao.update_status_by_doc_id(db, doc_id, status)

    @staticmethod
    async def delete(*, pk: list[int]) -> int:
        async with async_db_session.begin() as db:
            count = await upload_task_dao.delete(db, pk)
            return count


upload_task_service = UploadTaskService()