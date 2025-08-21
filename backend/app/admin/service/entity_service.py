#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from backend.app.admin.crud.crud_entity import entity_dao
from backend.app.admin.model.sys_entity import Entity
from backend.app.admin.schema.entity import CreateEntityParam, UpdateEntityParam
from backend.common.exception import errors
from backend.database.db_pg import async_db_session
from sqlalchemy import Select


class EntityService:
    @staticmethod
    async def get(*, pk: int) -> Entity:
        async with async_db_session() as db:
            entity = await entity_dao.get(db, pk)
            if not entity:
                raise errors.NotFoundError(msg='不存在')
            return entity
    
    @staticmethod
    async def get_select() -> Select:
        return await entity_dao.get_list()

    @staticmethod
    async def get_all() -> Sequence[Entity]:
        async with async_db_session() as db:
            entitys = await entity_dao.get_all(db)
            return entitys

    @staticmethod
    async def create(*, obj: CreateEntityParam) -> None:
        async with async_db_session.begin() as db:
            await entity_dao.create(db, obj)

    @staticmethod
    async def update(*, pk: int, obj: UpdateEntityParam) -> int:
        async with async_db_session.begin() as db:
            count = await entity_dao.update(db, pk, obj)
            return count

    @staticmethod
    async def delete(*, pk: list[int]) -> int:
        async with async_db_session.begin() as db:
            count = await entity_dao.delete(db, pk)
            return count


entity_service = EntityService()