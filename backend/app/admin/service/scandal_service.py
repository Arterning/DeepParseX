#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from sqlalchemy import Select

from backend.app.admin.crud.crud_scandal import scandal_crud
from backend.app.admin.model.sys_scandal import Scandal
from backend.app.admin.schema.scandal import CreateScandal, UpdateScandal
from backend.common.exception import errors
from backend.database.db_mysql import async_db_session


class ScandalService:
    @staticmethod
    async def get(*, pk: int) -> Scandal:
        async with async_db_session() as db:
            scandal = await scandal_crud.get(db, pk)
            if not scandal:
                raise errors.NotFoundError(msg=f"ID为{pk}的黑料不存在")
            return scandal

    @staticmethod
    async def get_by_name(name: str) -> Scandal:
        async with async_db_session() as db:
            scandal = await scandal_crud.get_by_name(db, name)
            return scandal

    @staticmethod
    async def get_select(*, name: str = None, content: str = None) -> Select:
        return await scandal_crud.get_list(name=name, content=content)

    @staticmethod
    async def get_all() -> Sequence[Scandal]:
        async with async_db_session() as db:
            scandals = await scandal_crud.get_all(db)
            return scandals

    @staticmethod
    async def create(*, obj: CreateScandal) -> None:
        async with async_db_session.begin() as db:
            await scandal_crud.create(db, obj)

    @staticmethod
    async def update(*, pk: int, obj: UpdateScandal) -> int:
        async with async_db_session.begin() as db:
            count = await scandal_crud.update(db, pk, obj)
            return count

    @staticmethod
    async def delete(*, pk: list[int]) -> int:
        async with async_db_session.begin() as db:
            count = await scandal_crud.delete(db, pk)
            return count


scandal_service = ScandalService()
