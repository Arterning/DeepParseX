#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model import SysDocDir, SysDoc
from backend.app.admin.schema.doc_dir import CreateDocDirParam, UpdateDocDirParam


class CRUDDocDir(CRUDPlus[SysDocDir]):
    async def get(self, db: AsyncSession, dir_id: int) -> SysDocDir | None:
        """
        获取目录

        :param db:
        :param dir_id:
        :return:
        """
        return await self.select_model_by_column(db, id=dir_id, del_flag=False)

    async def get_by_name(self, db: AsyncSession, name: str, parent_id: int = None) -> SysDocDir | None:
        """
        通过 name 和 parent_id 获取目录

        :param db:
        :param name:
        :param parent_id:
        :return:
        """
        if parent_id is not None:
            return await self.select_model_by_column(db, name=name, parent_id=parent_id, del_flag=False)
        else:
            return await self.select_model_by_column(db, name=name, parent_id=None, del_flag=False)

    async def get_all(self, db: AsyncSession, name: str = None) -> Sequence[SysDocDir]:
        """
        获取所有目录

        :param db:
        :param name:
        :return:
        """
        filters = {'del_flag__eq': False}
        if name is not None:
            filters.update(name__like=f'%{name}%')
        return await self.select_models_order(db, sort_columns='sort', **filters)

    async def create(self, db: AsyncSession, obj_in: CreateDocDirParam) -> None:
        """
        创建目录

        :param db:
        :param obj_in:
        :return:
        """
        await self.create_model(db, obj_in)

    async def update(self, db: AsyncSession, dir_id: int, obj_in: UpdateDocDirParam) -> int:
        """
        更新目录

        :param db:
        :param dir_id:
        :param obj_in:
        :return:
        """
        return await self.update_model(db, dir_id, obj_in)

    async def delete(self, db: AsyncSession, dir_id: int) -> int:
        """
        删除目录

        :param db:
        :param dir_id:
        :return:
        """
        return await self.delete_model_by_column(db, id=dir_id, logical_deletion=True, deleted_flag_column='del_flag')

    async def get_with_relation(self, db: AsyncSession, dir_id: int) -> list[SysDoc]:
        """
        获取关联

        :param db:
        :param dir_id:
        :return:
        """
        stmt = select(self.model).options(selectinload(self.model.docs)).where(self.model.id == dir_id)
        result = await db.execute(stmt)
        doc_relation = result.scalars().first()
        return doc_relation.docs

    async def get_children(self, db: AsyncSession, dir_id: int) -> list[SysDocDir]:
        """
        获取子目录

        :param db:
        :param dir_id:
        :return:
        """
        stmt = select(self.model).options(selectinload(self.model.children)).where(self.model.id == dir_id)
        result = await db.execute(stmt)
        doc_dir = result.scalars().first()
        return doc_dir.children


doc_dir_dao: CRUDDocDir = CRUDDocDir(SysDocDir)
