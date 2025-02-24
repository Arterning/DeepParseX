#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from sqlalchemy import Select, and_, desc, select, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model.sys_scandal import Scandal
from backend.app.admin.schema.scandal import CreateScandal, UpdateScandal


class CRUDScandal(CRUDPlus[Scandal]):
    async def get(self, db: AsyncSession, pk: int) -> Scandal | None:
        """
        获取黑料

        :param db:
        :param pk:
        :return:
        """
        # where = []
        # where.append(self.model.id == pk)
        res = await db.execute(
            select(self.model)
            .options(selectinload(self.model.person))
            .where(self.model.id == pk)
        )
        return res.scalars().first()
        # return await self.select_model_by_id(db, pk)

    async def get_list(self, name: str = None, content: str = None) -> Select:
        """
        获取黑料列表

        :param name: 人物名称
        :param content: 黑料内容
        :return:
        """
        se = select(self.model).order_by(desc(self.model.created_time))
        where_list = []
        if name:
            where_list.append(self.model.name.like(f'%{name}%'))
        if content:
            where_list.append(self.model.content.like(f'%{content}%'))
        if where_list:
            se = se.where(and_(*where_list))
        return se

    async def get_all(self, db: AsyncSession) -> Sequence[Scandal]:
        """
        获取所有黑料

        :param db:
        :return:
        """
        se = select(self.model).order_by(desc(self.model.created_time))
        result = await db.execute(se)
        return result.scalars().all()
    
    async def get_by_name(self, db: AsyncSession, name: str) -> Scandal | None:
        """
        根据名称获取黑料

        :param db:
        :param name:
        :return:
        """
        se = select(self.model).where(self.model.name == name)
        result = await db.execute(se)
        return result.scalar_one_or_none()
    
    async def create(self, db: AsyncSession, obj_in: CreateScandal) -> Scandal:
        """
        创建黑料

        :param db:
        :param obj_in:
        :return:
        """
        db_obj = await self.create_model(db, obj_in)
        return db_obj

    async def update(self, db: AsyncSession, pk: int, obj_in: UpdateScandal) -> int:
        """
        更新黑料

        :param db:
        :param pk:
        :param obj_in:
        :return:
        """
        return await self.update_model(db, pk, obj_in)

    async def delete(self, db: AsyncSession, pk: list[int]) -> int:
        """
        删除黑料

        :param db:
        :param pk:
        :return:
        """
        res = await db.execute(delete(self.model).where(self.model.id.in_(pk)))
        return res.rowcount


scandal_crud = CRUDScandal(Scandal)
