#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from sqlalchemy import delete, Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus
from sqlalchemy.orm import selectinload

from backend.app.admin.model.sys_entity import Entity
from backend.app.admin.schema.entity import CreateEntityParam, UpdateEntityParam


class CRUDEntity(CRUDPlus[Entity]):
    async def get(self, db: AsyncSession, pk: int) -> Entity | None:
        """
        获取 Entity 及其关联的文档

        :param db:
        :param pk:
        :return:
        """
        where = [self.model.id == pk]
        result = await db.execute(
            select(self.model)
            .options(selectinload(self.model.docs))
            .where(*where)
        )
        return result.scalars().first()

    async def get_list(self, name: str | None = None, entity_type: str | None = None) -> Select:
        """
        获取实体列表

        :param name: 实体名称（模糊匹配）
        :param entity_type: 实体类型
        :return:
        """
        whereclause = {}
        
        if name:
            whereclause.update(name__like=f'%{name}%')
        
        if entity_type:
            whereclause.update(entity_type__like=f'%{entity_type}%')
        
        return await self.select_order('created_time', 'desc', **whereclause)

    async def get_all(self, db: AsyncSession) -> Sequence[Entity]:
        """
        获取所有 Entity

        :param db:
        :return:
        """
        return await self.select_models(db)

    async def create(self, db: AsyncSession, obj_in: CreateEntityParam) -> None:
        """
        创建 Entity

        :param db:
        :param obj_in:
        :return:
        """
        await self.create_model(db, obj_in)

    async def update(self, db: AsyncSession, pk: int, obj_in: UpdateEntityParam) -> int:
        """
        更新 Entity

        :param db:
        :param pk:
        :param obj_in:
        :return:
        """
        return await self.update_model(db, pk, obj_in)

    async def delete(self, db: AsyncSession, pk: list[int]) -> int:
        """
        删除 Entity

        :param db:
        :param pk:
        :return:
        """
        return  await self.delete_model_by_column(db, allow_multiple=True, id__in=pk)


entity_dao: CRUDEntity = CRUDEntity(Entity)