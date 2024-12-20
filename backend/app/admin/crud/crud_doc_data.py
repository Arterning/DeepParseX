#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model import SysDocData
from backend.app.admin.schema.doc_data import CreateSysDocDataParam, UpdateSysDocDataParam


class CRUDSysDocData(CRUDPlus[SysDocData]):
    async def get(self, db: AsyncSession, pk: int) -> SysDocData | None:
        """
        获取 SysDocData

        :param db:
        :param pk:
        :return:
        """
        return await self.select_model(db, pk)

    async def get_all(self, db: AsyncSession) -> Sequence[SysDocData]:
        """
        获取所有 SysDocData

        :param db:
        :return:
        """
        return await self.select_models(db)

    async def create(self, db: AsyncSession, obj_in: CreateSysDocDataParam) -> SysDocData:
        """
        创建 SysDocData

        :param db:
        :param obj_in:
        :return:
        """
        return await self.create_model(db, obj_in)
    
    async def create_bulk(self, db: AsyncSession, obj_list: list[CreateSysDocDataParam]) -> list[SysDocData]:
        """
        批量创建 SysDocChunk
        :param db: 数据库会话
        :param obj_list: 要插入的对象列表
        :return: 插入后的 SysDocChunk 列表
        """
        return await self.create_models(db,obj_list)

    async def update(self, db: AsyncSession, pk: int, obj_in: UpdateSysDocDataParam) -> int:
        """
        更新 SysDocData

        :param db:
        :param pk:
        :param obj_in:
        :return:
        """
        return await self.update_model(db, pk, obj_in)

    async def delete(self, db: AsyncSession, doc_id: list[int]) -> int:
        """
        删除 SysDocData

        :param db:
        :param pk:
        :return:
        """
        return  await self.delete_model_by_column(db, allow_multiple=True, doc_id__in=doc_id)


sys_doc_data_dao: CRUDSysDocData = CRUDSysDocData(SysDocData)
