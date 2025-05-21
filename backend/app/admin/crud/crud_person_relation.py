#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from sqlalchemy import delete, Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model.sys_person_relation import PersonRelation
from backend.app.admin.schema.person_relation import CreatePersonRelationParam, UpdatePersonRelationParam


class CRUDPersonRelation(CRUDPlus[PersonRelation]):
    async def get(self, db: AsyncSession, pk: int) -> PersonRelation | None:
        """
        获取 PersonRelation

        :param db:
        :param pk:
        :return:
        """
        return await self.select_model(db, pk)

    async def get_list(self) -> Select:
        """
        获取新闻列表

        :return:
        """
        return await self.select_order('created_time', 'desc')

    async def get_all(self, db: AsyncSession) -> Sequence[PersonRelation]:
        """
        获取所有 PersonRelation

        :param db:
        :return:
        """
        return await self.select_models(db)

    async def create(self, db: AsyncSession, obj_in: CreatePersonRelationParam) -> None:
        """
        创建 PersonRelation

        :param db:
        :param obj_in:
        :return:
        """
        await self.create_model(db, obj_in)

    async def update(self, db: AsyncSession, pk: int, obj_in: UpdatePersonRelationParam) -> int:
        """
        更新 PersonRelation

        :param db:
        :param pk:
        :param obj_in:
        :return:
        """
        return await self.update_model(db, pk, obj_in)

    async def delete(self, db: AsyncSession, pk: list[int]) -> int:
        """
        删除 PersonRelation

        :param db:
        :param pk:
        :return:
        """
        return  await self.delete_model_by_column(db, allow_multiple=True, id__in=pk)


person_relation_dao: CRUDPersonRelation = CRUDPersonRelation(PersonRelation)