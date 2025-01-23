#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from backend.app.admin.crud.crud_event import event_dao
from backend.app.admin.model.event import Event
from backend.app.admin.schema.event import CreateEventParam, UpdateEventParam
from backend.common.exception import errors
from backend.database.db_pg import async_db_session
from sqlalchemy import Select


class EventService:
    @staticmethod
    async def get(*, pk: int) -> Event:
        async with async_db_session() as db:
            event = await event_dao.get(db, pk)
            if not event:
                raise errors.NotFoundError(msg='不存在')
            return event
    
    @staticmethod
    async def get_select() -> Select:
        return await event_dao.get_list()

    @staticmethod
    async def get_all() -> Sequence[Event]:
        async with async_db_session() as db:
            events = await event_dao.get_all(db)
            return events

    @staticmethod
    async def create(*, obj: CreateEventParam) -> None:
        async with async_db_session.begin() as db:
            await event_dao.create(db, obj)

    @staticmethod
    async def update(*, pk: int, obj: UpdateEventParam) -> int:
        async with async_db_session.begin() as db:
            count = await event_dao.update(db, pk, obj)
            return count

    @staticmethod
    async def delete(*, pk: list[int]) -> int:
        async with async_db_session.begin() as db:
            count = await event_dao.delete(db, pk)
            return count


event_service = EventService()