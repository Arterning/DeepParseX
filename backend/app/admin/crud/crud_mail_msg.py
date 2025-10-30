#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Sequence

from sqlalchemy import Select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model.mail_msg import MailMsg
from backend.app.admin.schema.mail_msg import CreateMailMsgParam, UpdateMailMsgParam


class CRUDMailMsg(CRUDPlus[MailMsg]):
    async def get(self, db: AsyncSession, pk: int) -> MailMsg | None:
        """
        获取 MailMsg

        :param db:
        :param pk:
        :return:
        """
        return await self.select_model(db, pk)

    async def get_list(
        self,
        name: str | None = None,
        subject: str | None = None,
        time: datetime | None = None,
        category: str | None = None,
        sender: str | None = None,
        receiver: str | None = None,
        cc: str | None = None,
        bcc: str | None = None,
        doc_dir_id: int | None = None,
        current_user_id: int | None = None
    ) -> Select:
        """
        获取邮件列表
        
        :param current_user_id: 当前登录用户ID，用于权限过滤
        :return:
        """
        select_stmt = await self.select_order('created_time', 'desc')
        
        # 只有指定了current_user_id时，才进行用户权限过滤
        # 根据model.py中的UserMixin，邮件应该有create_user字段表示创建者
        if current_user_id is not None:
            select_stmt = select_stmt.where(self.model.create_user == current_user_id)
        
        if name:
            select_stmt = select_stmt.where(self.model.name.like(f'%{name}%'))
        if subject:
            select_stmt = select_stmt.where(self.model.subject.like(f'%{subject}%'))
        if time:
            select_stmt = select_stmt.where(func.date(self.model.time) >= time.date())
        if category:
            select_stmt = select_stmt.where(self.model.category.like(f'%{category}%'))
        if sender:
            select_stmt = select_stmt.where(self.model.sender.like(f'%{sender}%'))
        if receiver:
            select_stmt = select_stmt.where(self.model.receiver.like(f'%{receiver}%'))
        if cc:
            select_stmt = select_stmt.where(self.model.cc.like(f'%{cc}%'))
        if bcc:
            select_stmt = select_stmt.where(self.model.bcc.like(f'%{bcc}%'))
        if doc_dir_id:
            select_stmt = select_stmt.where(self.model.doc_dir_id == doc_dir_id)
        return select_stmt

    async def get_all(self, db: AsyncSession) -> Sequence[MailMsg]:
        """
        获取所有 MailMsg

        :param db:
        :return:
        """
        return await self.select_models(db)

    async def create(self, db: AsyncSession, obj_in: CreateMailMsgParam) -> None:
        """
        创建 MailMsg

        :param db:
        :param obj_in:
        :return:
        """
        await self.create_model(db, obj_in)

    async def update(self, db: AsyncSession, pk: int, obj_in: UpdateMailMsgParam) -> int:
        """
        更新 MailMsg

        :param db:
        :param pk:
        :param obj_in:
        :return:
        """
        return await self.update_model(db, pk, obj_in)

    async def base_update(self, db: AsyncSession, pk: int, obj_in: dict) -> int:
        return await self.update_model(db, pk, obj_in)
        
    async def delete(self, db: AsyncSession, pk: list[int]) -> int:
        """
        删除 MailMsg

        :param db:
        :param pk:
        :return:
        """
        return  await self.delete_model_by_column(db, allow_multiple=True, id__in=pk)


mail_msg_dao: CRUDMailMsg = CRUDMailMsg(MailMsg)