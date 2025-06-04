#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from sqlalchemy import delete, Select, select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus
from sqlalchemy.orm import selectinload
from backend.app.admin.model.sys_star_collect import StarCollect
from backend.app.admin.schema.star_collect import CreateStarCollectParam, UpdateStarCollectParam


class CRUDStarCollect(CRUDPlus[StarCollect]):
    async def get(self, db: AsyncSession, pk: int) -> StarCollect | None:
        """
        获取 StarCollect

        :param db:
        :param pk:
        :return:
        """
        return await self.select_model(db, pk)

    async def get_list(self) -> Select:
        """
        获取收藏列表

        :return:
        """
        se = (
            select(self.model)
                .options(selectinload(self.model.docs))
                .order_by(desc(self.model.created_time))
        )
        return se

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