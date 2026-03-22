#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence
from datetime import datetime, timedelta

from sqlalchemy import delete, update as sa_update, Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model.sys_upload_task import UploadTask
from backend.app.admin.schema.upload_task import CreateUploadTaskParam, UpdateUploadTaskParam


class CRUDUploadTask(CRUDPlus[UploadTask]):
    async def get(self, db: AsyncSession, pk: int) -> UploadTask | None:
        """
        获取 UploadTask

        :param db:
        :param pk:
        :return:
        """
        return await self.select_model(db, pk)

    async def get_list(self, name: str | None = None, status: str | None = None, source: str | None = None, rangeValue: list[str] | None = None, create_user: int | None = None) -> Select:
        """
        获取上传任务列表

        :param name: 任务名称（模糊搜索）
        :param status: 任务状态
        :param source: 任务来源
        :param rangeValue: 时间范围，格式为 ['2023-01-01', '2023-01-02']
        :param create_user: 创建者ID，用于权限过滤
        :return:
        """
        query = await self.select_order('created_time', 'desc')
        start_time = rangeValue[0]
        end_time = rangeValue[1]
        if create_user is not None:
            query = query.where(UploadTask.create_user == create_user)
        if name:
            query = query.where(UploadTask.name.like(f'%{name}%'))
        if status:
            query = query.where(UploadTask.status == status)
        if source:
            query = query.where(UploadTask.source.like(f'%{source}%'))
        if start_time:
            start_dt = datetime.strptime(start_time, '%Y-%m-%d')
            query = query.where(UploadTask.created_time >= start_dt)
        if end_time:
            end_dt = datetime.strptime(end_time, '%Y-%m-%d') + timedelta(hours=23, minutes=59, seconds=59)
            query = query.where(UploadTask.created_time <= end_dt)
        return query

    async def get_all(self, db: AsyncSession) -> Sequence[UploadTask]:
        """
        获取所有 UploadTask

        :param db:
        :return:
        """
        return await self.select_models(db)

    async def create(self, db: AsyncSession, obj_in: CreateUploadTaskParam) -> UploadTask:
        """
        创建 UploadTask

        :param db:
        :param obj_in:
        :return:
        """
        # return await self.create_model(db, obj_in)
        dict_obj = obj_in.model_dump()
        task = self.model(**dict_obj)
        db.add(task)
        return task
        

    async def update(self, db: AsyncSession, pk: int, obj_in: UpdateUploadTaskParam) -> int:
        """
        更新 UploadTask

        :param db:
        :param pk:
        :param obj_in:
        :return:
        """
        return await self.update_model(db, pk, obj_in)

    async def update_status_by_doc_id(self, db: AsyncSession, doc_id: int, status: str) -> int:
        """按 doc_id 更新任务状态，无需先查询"""
        stmt = sa_update(self.model).where(self.model.doc_id == doc_id).values(status=status)
        result = await db.execute(stmt)
        return result.rowcount

    async def delete(self, db: AsyncSession, pk: list[int]) -> int:
        """
        删除 UploadTask

        :param db:
        :param pk:
        :return:
        """
        return  await self.delete_model_by_column(db, allow_multiple=True, id__in=pk)


upload_task_dao: CRUDUploadTask = CRUDUploadTask(UploadTask)