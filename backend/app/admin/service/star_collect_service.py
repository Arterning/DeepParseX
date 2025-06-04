#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from backend.app.admin.crud.crud_star_collect import star_collect_dao
from backend.app.admin.model.sys_star_collect import StarCollect
from backend.app.admin.schema.star_collect import CreateStarCollectParam, UpdateStarCollectParam
from backend.common.exception import errors
from backend.database.db_pg import async_db_session
from sqlalchemy import Select


class StarCollectService:
    @staticmethod
    async def get(*, pk: int) -> StarCollect:
        async with async_db_session() as db:
            star_collect = await star_collect_dao.get(db, pk)
            if not star_collect:
                raise errors.NotFoundError(msg='不存在')
            return star_collect
    
    @staticmethod
    async def get_select() -> Select:
        return await star_collect_dao.get_list()

    @staticmethod
    async def get_all() -> Sequence[StarCollect]:
        async with async_db_session() as db:
            star_collects = await star_collect_dao.get_all(db)
            return star_collects

    @staticmethod
    async def create(*, obj: CreateStarCollectParam) -> None:
        async with async_db_session.begin() as db:
            await star_collect_dao.create(db, obj)

    @staticmethod
    async def update(*, pk: int, obj: UpdateStarCollectParam) -> int:
        async with async_db_session.begin() as db:
            count = await star_collect_dao.update(db, pk, obj)
            return count

    @staticmethod
    async def delete(*, pk: list[int]) -> int:
        async with async_db_session.begin() as db:
            count = await star_collect_dao.delete(db, pk)
            return count


star_collect_service = StarCollectService()