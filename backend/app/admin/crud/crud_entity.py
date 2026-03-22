#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from sqlalchemy import delete, func, Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus
from sqlalchemy.orm import selectinload

from backend.app.admin.model.sys_entity import Entity
from backend.app.admin.model.sys_entity_doc import sys_entity_doc
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

    async def get_list(self, name: str | None = None, entity_type: str | list[str] | None = None, eml: bool | None = None, create_user: int | None = None) -> Select:
        """
        获取实体列表，按关联文档数量降序排列

        :param name: 实体名称（模糊匹配）
        :param entity_type: 实体类型，支持单个字符串或字符串数组
        :param eml: 是否仅显示关联邮件的实体
        :return:
        """
        # 子查询：统计每个实体关联的文档数量
        doc_count_sub = (
            select(
                sys_entity_doc.c.entity_id,
                func.count(sys_entity_doc.c.doc_id).label('doc_count'),
            )
            .group_by(sys_entity_doc.c.entity_id)
            .subquery()
        )

        # 主查询：左连接子查询，按文档数量降序
        stmt = (
            select(Entity)
            .outerjoin(doc_count_sub, Entity.id == doc_count_sub.c.entity_id)
        )

        # 动态添加过滤条件
        if name:
            stmt = stmt.where(Entity.name.like(f'%{name}%'))
        if eml:
            stmt = stmt.where(Entity.source_doc_name.like('%eml%'))
        if entity_type:
            if isinstance(entity_type, list):
                stmt = stmt.where(Entity.entity_type.in_(entity_type))
            else:
                stmt = stmt.where(Entity.entity_type.like(f'%{entity_type}%'))
        if create_user is not None:
            stmt = stmt.where(Entity.create_user == create_user)

        # 按关联文档数降序，文档数相同则按创建时间降序
        stmt = stmt.order_by(
            func.coalesce(doc_count_sub.c.doc_count, 0).desc(),
            Entity.created_time.desc(),
        )

        return stmt

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
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pk)

    async def delete_owned(self, db: AsyncSession, pk: list[int], owner_id: int) -> int:
        return await self.delete_model_by_column(
            db, allow_multiple=True, id__in=pk, create_user=owner_id
        )

    async def update_properties(self, db: AsyncSession, pk: int, properties: dict, description: str | None = None, profile: str | None = None) -> int:
        """
        更新 Entity 的 properties、description 和 profile 字段

        :param db:
        :param pk:
        :param properties:
        :param description:
        :param profile:
        :return:
        """
        update_data = {'properties': properties}
        if description is not None:
            update_data['description'] = description
        if profile is not None:
            update_data['profile'] = profile
        return await self.update_model(db, pk, update_data)


    async def get_distinct_types(self, db: AsyncSession) -> list[str]:
        """
        获取所有实体中去重后的 entity_type 列表（group by 查询）
        """
        result = await db.execute(
            select(self.model.entity_type)
            .where(self.model.entity_type.is_not(None))
            .group_by(self.model.entity_type)
            .order_by(self.model.entity_type)
        )
        return [row[0] for row in result.all()]

    async def get_type_stats(self, db: AsyncSession) -> list[dict]:
        """
        获取各实体类型的数量统计
        """
        result = await db.execute(
            select(self.model.entity_type, func.count().label('count'))
            .group_by(self.model.entity_type)
            .order_by(func.count().desc())
        )
        return [{'entity_type': row[0] or '未分类', 'count': row[1]} for row in result.all()]


entity_dao: CRUDEntity = CRUDEntity(Entity)