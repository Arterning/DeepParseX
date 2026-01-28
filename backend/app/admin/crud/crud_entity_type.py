#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import List

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model import EntityType
from backend.app.admin.schema.entity_type import CreateEntityTypeParam, UpdateEntityTypeParam


class CRUDEntityType(CRUDPlus[EntityType]):
    async def get(self, db: AsyncSession, pk: int) -> EntityType | None:
        """获取单个实体类型"""
        return await self.select_model(db, pk)

    async def get_list(
        self, name: str | None = None
    ) -> Select:
        """获取实体类型列表"""
        filters = {}
        if name is not None:
            filters.update(name__like=f'%{name}%')
        return await self.select_order('created_time', 'desc', **filters)

    async def get_by_name(self, db: AsyncSession, name: str) -> EntityType | None:
        """根据名称获取实体类型"""
        return await self.select_model_by_column(db, name=name)

    async def create(self, db: AsyncSession, obj_in: CreateEntityTypeParam) -> None:
        """创建实体类型"""
        await self.create_model(db, obj_in)

    async def update(self, db: AsyncSession, pk: int, obj_in: UpdateEntityTypeParam) -> int:
        """更新实体类型"""
        return await self.update_model(db, pk, obj_in)

    async def delete(self, db: AsyncSession, pk: List[int]) -> int:
        """删除实体类型"""
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pk)


entity_type_dao: CRUDEntityType = CRUDEntityType(EntityType)
