#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from backend.app.admin.crud.crud_mail_box import mail_box_dao
from backend.app.admin.model.mail_box import MailBox
from backend.app.admin.schema.mail_box import CreateMailBoxParam, UpdateMailBoxParam
from backend.common.exception import errors
from backend.database.db_pg import async_db_session
from sqlalchemy import Select


class MailBoxService:
    @staticmethod
    async def get(*, pk: int) -> MailBox:
        async with async_db_session() as db:
            mail_box = await mail_box_dao.get(db, pk)
            if not mail_box:
                raise errors.NotFoundError(msg='不存在')
            return mail_box
    
    @staticmethod
    async def get_select() -> Select:
        return await mail_box_dao.get_list()

    @staticmethod
    async def get_all() -> Sequence[MailBox]:
        async with async_db_session() as db:
            mail_boxs = await mail_box_dao.get_all(db)
            return mail_boxs

    @staticmethod
    async def create(*, obj: CreateMailBoxParam) -> None:
        async with async_db_session.begin() as db:
            found = await mail_box_dao.get_by_name(db, obj.name)
            if found:
                return
            await mail_box_dao.create(db, obj)

    @staticmethod
    async def update(*, pk: int, obj: UpdateMailBoxParam) -> int:
        async with async_db_session.begin() as db:
            count = await mail_box_dao.update(db, pk, obj)
            return count

    @staticmethod
    async def delete(*, pk: list[int]) -> int:
        async with async_db_session.begin() as db:
            count = await mail_box_dao.delete(db, pk)
            return count


mail_box_service = MailBoxService()