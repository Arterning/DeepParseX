#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from backend.app.admin.crud.crud_mail_msg import mail_msg_dao
from backend.app.admin.model.mail_msg import MailMsg
from backend.app.admin.schema.mail_msg import CreateMailMsgParam, UpdateMailMsgParam
from backend.common.exception import errors
from backend.database.db_pg import async_db_session
from sqlalchemy import Select


class MailMsgService:
    @staticmethod
    async def get(*, pk: int) -> MailMsg:
        async with async_db_session() as db:
            mail_msg = await mail_msg_dao.get(db, pk)
            if not mail_msg:
                raise errors.NotFoundError(msg='不存在')
            return mail_msg
    
    @staticmethod
    async def get_select() -> Select:
        return await mail_msg_dao.get_list()

    @staticmethod
    async def get_all() -> Sequence[MailMsg]:
        async with async_db_session() as db:
            mail_msgs = await mail_msg_dao.get_all(db)
            return mail_msgs

    @staticmethod
    async def create(*, obj: CreateMailMsgParam) -> None:
        async with async_db_session.begin() as db:
            await mail_msg_dao.create(db, obj)

    @staticmethod
    async def update(*, pk: int, obj: UpdateMailMsgParam) -> int:
        async with async_db_session.begin() as db:
            count = await mail_msg_dao.update(db, pk, obj)
            return count

    @staticmethod
    async def delete(*, pk: list[int]) -> int:
        async with async_db_session.begin() as db:
            count = await mail_msg_dao.delete(db, pk)
            return count


mail_msg_service = MailMsgService()