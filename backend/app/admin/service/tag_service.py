#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from backend.app.admin.crud.crud_tag import tag_dao
from backend.app.admin.model.sys_tag import Tag
from backend.app.admin.schema.tag import CreateTagParam, UpdateTagParam
from backend.common.exception import errors
from backend.database.db_pg import async_db_session
from sqlalchemy import Select


class TagService:
    @staticmethod
    async def get(*, pk: int) -> Tag:
        async with async_db_session() as db:
            tag = await tag_dao.get(db, pk)
            if not tag:
                raise errors.NotFoundError(msg='不存在')
            return tag
    
    @staticmethod
    async def get_select() -> Select:
        return await tag_dao.get_list()

    @staticmethod
    async def get_all() -> Sequence[Tag]:
        async with async_db_session() as db:
            tags = await tag_dao.get_all(db)
            return tags

    @staticmethod
    async def create(*, obj: CreateTagParam) -> None:
        async with async_db_session.begin() as db:
            await tag_dao.create(db, obj)

    @staticmethod
    async def update(*, pk: int, obj: UpdateTagParam) -> int:
        async with async_db_session.begin() as db:
            count = await tag_dao.update(db, pk, obj)
            return count

    @staticmethod
    async def delete(*, pk: list[int]) -> int:
        async with async_db_session.begin() as db:
            count = await tag_dao.delete(db, pk)
            return count


tag_service = TagService()