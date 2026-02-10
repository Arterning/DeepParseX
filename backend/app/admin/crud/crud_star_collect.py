#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from sqlalchemy import delete, Select, select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus
from sqlalchemy.orm import selectinload
from backend.app.admin.model.sys_star_collect import StarCollect
from backend.app.admin.model.sys_star_entity import sys_star_entity
from backend.app.admin.schema.star_collect import CreateStarCollectParam, UpdateStarCollectParam


class CRUDStarCollect(CRUDPlus[StarCollect]):
    async def get(self, db: AsyncSession, pk: int) -> StarCollect | None:
        """
        获取 StarCollect

        :param db:
        :param pk:
        :return:
        """
        where = [self.model.id == pk]
        doc = await db.execute(
            select(self.model)
            .options(selectinload(self.model.docs), selectinload(self.model.entities))
            .where(*where)
        )
        return doc.scalars().first()

    async def get_list(self) -> Select:
        """
        获取收藏列表

        :return:
        """
        se = (
            select(self.model)
                .options(selectinload(self.model.docs), selectinload(self.model.entities))
                .order_by(desc(self.model.created_time))
        )
        return se

    async def add_entity(self, db: AsyncSession, star_id: int, entity_id: int, created_by: int | None = None) -> bool:
        """
        添加实体到收藏夹

        :param db:
        :param star_id:
        :param entity_id:
        :param created_by:
        :return:
        """
        # 检查是否已存在
        existing = await db.execute(
            select(sys_star_entity).where(
                sys_star_entity.c.star_id == star_id,
                sys_star_entity.c.entity_id == entity_id
            )
        )
        if existing.first():
            return False

        await db.execute(
            sys_star_entity.insert().values(
                star_id=star_id,
                entity_id=entity_id,
                created_by=created_by
            )
        )
        return True

    async def remove_entity(self, db: AsyncSession, star_id: int, entity_id: int) -> bool:
        """
        从收藏夹移除实体

        :param db:
        :param star_id:
        :param entity_id:
        :return:
        """
        result = await db.execute(
            delete(sys_star_entity).where(
                sys_star_entity.c.star_id == star_id,
                sys_star_entity.c.entity_id == entity_id
            )
        )
        return result.rowcount > 0

    async def get_entity_starred_ids(self, db: AsyncSession, entity_id: int) -> list[int]:
        """
        获取实体所在的所有收藏夹ID列表

        :param db:
        :param entity_id:
        :return: 收藏夹ID列表
        """
        result = await db.execute(
            select(sys_star_entity.c.star_id).where(
                sys_star_entity.c.entity_id == entity_id
            )
        )
        return [row[0] for row in result.fetchall()]

    async def get_all(self, db: AsyncSession) -> Sequence[StarCollect]:
        """
        获取所有 StarCollect

        :param db:
        :return:
        """
        return await self.select_models(db)

    async def create(self, db: AsyncSession, obj_in: CreateStarCollectParam) -> None:
        """
        创建 StarCollect

        :param db:
        :param obj_in:
        :return:
        """
        await self.create_model(db, obj_in)

    async def update(self, db: AsyncSession, pk: int, obj_in: UpdateStarCollectParam) -> int:
        """
        更新 StarCollect

        :param db:
        :param pk:
        :param obj_in:
        :return:
        """
        return await self.update_model(db, pk, obj_in)

    async def delete(self, db: AsyncSession, pk: list[int]) -> int:
        """
        删除 StarCollect

        :param db:
        :param pk:
        :return:
        """
        return  await self.delete_model_by_column(db, allow_multiple=True, id__in=pk)


star_collect_dao: CRUDStarCollect = CRUDStarCollect(StarCollect)