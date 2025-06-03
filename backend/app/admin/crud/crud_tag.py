#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from sqlalchemy import delete, Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model.sys_tag import Tag
from backend.app.admin.schema.tag import CreateTagParam, UpdateTagParam


class CRUDTag(CRUDPlus[Tag]):
    async def get(self, db: AsyncSession, pk: int) -> Tag | None:
        """
        获取 Tag

        :param db:
        :param pk:
        :return:
        """
        return await self.select_model(db, pk)

    async def get_list(self) -> Select:
        """
        获取标签列表

        :return:
        """
        return await self.select_order('created_time', 'desc')

    async def get_all(self, db: AsyncSession) -> Sequence[Tag]:
        """
        获取所有 Tag

        :param db:
        :return:
        """
        return await self.select_models(db)

    async def create(self, db: AsyncSession, obj_in: CreateTagParam) -> None:
        """
        创建 Tag

        :param db:
        :param obj_in:
        :return:
        """
        await self.create_model(db, obj_in)

    async def update(self, db: AsyncSession, pk: int, obj_in: UpdateTagParam) -> int:
        """
        更新 Tag

        :param db:
        :param pk:
        :param obj_in:
        :return:
        """
        return await self.update_model(db, pk, obj_in)

    async def delete(self, db: AsyncSession, pk: list[int]) -> int:
        """
        删除 Tag

        :param db:
        :param pk:
        :return:
        """
        return  await self.delete_model_by_column(db, allow_multiple=True, id__in=pk)

    async def get_by_name(self, db: AsyncSession, name: str) -> Tag | None:
        """
        通过 name 获取 Tag

        :param db:
        :param name:
        :return:
        """
        query = await db.execute(select(self.model).where(self.model.name == name))
        return query.scalars().first()

    async def get_or_create_by_name(self, db: AsyncSession, name: str) -> Tag | None:
        """
        通过 name 获取 Tag 或创建

        :param db:
        :param name:
        :return:
        """
        tag = await self.get_by_name(db, name)
        if tag:
            return tag
        param = CreateTagParam(name=name)
        tag = self.model(**param.model_dump())
        db.add(tag)
        return tag

tag_dao: CRUDTag = CRUDTag(Tag)