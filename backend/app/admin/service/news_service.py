#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from backend.app.admin.crud.crud_news import news_dao
from backend.app.admin.model.sys_news import News
from backend.app.admin.schema.news import CreateNewsParam, UpdateNewsParam
from backend.common.exception import errors
from backend.database.db_pg import async_db_session
from sqlalchemy import Select


class NewsService:
    @staticmethod
    async def get(*, pk: int) -> News:
        async with async_db_session() as db:
            news = await news_dao.get(db, pk)
            if not news:
                raise errors.NotFoundError(msg='不存在')
            return news
    
    @staticmethod
    async def get_select() -> Select:
        return await news_dao.get_list()

    @staticmethod
    async def get_all() -> Sequence[News]:
        async with async_db_session() as db:
            newss = await news_dao.get_all(db)
            return newss

    @staticmethod
    async def create(*, obj: CreateNewsParam) -> None:
        async with async_db_session.begin() as db:
            await news_dao.create(db, obj)

    @staticmethod
    async def update(*, pk: int, obj: UpdateNewsParam) -> int:
        async with async_db_session.begin() as db:
            count = await news_dao.update(db, pk, obj)
            return count

    @staticmethod
    async def delete(*, pk: list[int]) -> int:
        async with async_db_session.begin() as db:
            count = await news_dao.delete(db, pk)
            return count


news_service = NewsService()