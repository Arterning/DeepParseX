#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin.crud.crud_entity_type import entity_type_dao
from backend.app.admin.model import EntityType
from backend.app.admin.schema.entity_type import CreateEntityTypeParam, UpdateEntityTypeParam
from backend.common.exception import errors
from backend.database.db_pg import async_db_session


class EntityTypeService:
    """实体类型服务"""

    @staticmethod
    async def get(*, pk: int) -> EntityType:
        """获取实体类型详情"""
        async with async_db_session() as db:
            entity_type = await entity_type_dao.get(db, pk)
            if not entity_type:
                raise errors.NotFoundError(msg='实体类型不存在')
            return entity_type

    @staticmethod
    async def get_select(*, name: str | None = None):
        """获取实体类型列表（用于分页查询）"""
        return await entity_type_dao.get_list(name=name)

    @staticmethod
    async def get_by_name(*, name: str) -> EntityType | None:
        """根据名称获取实体类型"""
        async with async_db_session() as db:
            return await entity_type_dao.get_by_name(db, name)

    @staticmethod
    async def create(*, obj: CreateEntityTypeParam) -> None:
        """创建实体类型"""
        async with async_db_session.begin() as db:
            # 检查名称是否已存在
            existing = await entity_type_dao.get_by_name(db, obj.name)
            if existing:
                raise errors.ForbiddenError(msg='实体类型名称已存在')
            await entity_type_dao.create(db, obj)

    @staticmethod
    async def update(*, pk: int, obj: UpdateEntityTypeParam) -> int:
        """更新实体类型"""
        async with async_db_session.begin() as db:
            # 检查实体类型是否存在
            entity_type = await entity_type_dao.get(db, pk)
            if not entity_type:
                raise errors.NotFoundError(msg='实体类型不存在')

            # 如果更新了名称，检查新名称是否已被其他实体类型使用
            if obj.name and obj.name != entity_type.name:
                existing = await entity_type_dao.get_by_name(db, obj.name)
                if existing:
                    raise errors.ForbiddenError(msg='实体类型名称已存在')

            return await entity_type_dao.update(db, pk, obj)

    @staticmethod
    async def delete(*, pk: List[int]) -> int:
        """删除实体类型"""
        async with async_db_session.begin() as db:
            return await entity_type_dao.delete(db, pk)


# 创建服务单例
entity_type_service = EntityTypeService()
