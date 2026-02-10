#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Sequence, List, Set

from backend.app.admin.crud.crud_mail_msg import mail_msg_dao
from backend.app.admin.model.mail_msg import MailMsg
from backend.app.admin.schema.mail_msg import CreateMailMsgParam, UpdateMailMsgParam
from backend.app.admin.service.doc_service import sys_doc_service
from backend.common.exception import errors
from backend.database.db_pg import async_db_session
from sqlalchemy import Select, select


class MailMsgService:
    @staticmethod
    async def get(*, pk: int) -> MailMsg:
        async with async_db_session() as db:
            mail_msg = await mail_msg_dao.get(db, pk)
            if not mail_msg:
                raise errors.NotFoundError(msg='不存在')
            return mail_msg
    
    @staticmethod
    async def get_select(
        *,
        name: str | None = None,
        subject: str | None = None,
        time: datetime | None = None,
        category: str | None = None,
        sender: str | None = None,
        receiver: str | None = None,
        cc: str | None = None,
        bcc: str | None = None,
        doc_dir_id: int | None = None,
        detection_result: int | None = None,
        current_user_id: int | None = None,
    ) -> Select:
        return await mail_msg_dao.get_list(
            name=name,
            subject=subject,
            time=time,
            category=category,
            sender=sender,
            receiver=receiver,
            cc=cc,
            bcc=bcc,
            doc_dir_id=doc_dir_id,
            detection_result=detection_result,
            current_user_id=current_user_id,
        )

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
    async def base_update(*, pk: int, obj: dict) -> int:
        async with async_db_session.begin() as db:
            count = await mail_msg_dao.base_update(db, pk, obj)
            return count


    @staticmethod
    async def delete(*, pk: list[int]) -> int:
        async with async_db_session.begin() as db:
            # 先查询要删除的邮件记录，获取关联的doc_id
            stmt = select(MailMsg.doc_id).where(MailMsg.id.in_(pk))
            result = await db.execute(stmt)
            doc_ids = [doc_id for doc_id in result.scalars().all() if doc_id is not None]
            
            # 如果有关联的文档，先删除文档
            if doc_ids:
                await sys_doc_service.delete(pk=doc_ids)
            
            # 然后删除邮件记录
            count = await mail_msg_dao.delete(db, pk)
            return count


mail_msg_service = MailMsgService()