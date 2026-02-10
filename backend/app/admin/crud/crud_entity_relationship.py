#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from sqlalchemy import delete, Select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model.sys_entity_relationship import EntityRelation


class CRUDEntityRelation(CRUDPlus[EntityRelation]):
    async def get_by_entity_id(self, db: AsyncSession, entity_id: int) -> Sequence[EntityRelation]:
        """
        获取指定实体ID的所有关系
        
        :param db:
        :param entity_id:
        :return:
        """
        stmt = (
            Select(self.model)
            .where(or_(self.model.source_id == entity_id, self.model.target_id == entity_id))
            .order_by(self.model.id)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_entity_ids(self, db: AsyncSession, entity_ids: list[int]) -> Sequence[EntityRelation]:
        """
        获取 source_id 或 target_id 在给定 ID 列表中的所有关系记录

        :param db:
        :param entity_ids:
        :return:
        """
        stmt = (
            Select(self.model)
            .where(or_(self.model.source_id.in_(entity_ids), self.model.target_id.in_(entity_ids)))
            .order_by(self.model.id)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get(self, db: AsyncSession, pk: int) -> EntityRelation | None:
        """
        获取关系详情
        
        :param db:
        :param pk:
        :return:
        """
        return await self.select_model(db, pk)

    async def delete(self, db: AsyncSession, pk: list[int]) -> int:
        """
        删除关系
        
        :param db:
        :param pk:
        :return:
        """
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pk)


entity_relation_dao: CRUDEntityRelation = CRUDEntityRelation(EntityRelation)