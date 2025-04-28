#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from sqlalchemy import delete, Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model.mail_box import MailBox
from backend.app.admin.schema.mail_box import CreateMailBoxParam, UpdateMailBoxParam


class CRUDMailBox(CRUDPlus[MailBox]):

    async def get_by_name(self, db: AsyncSession, name: str) -> MailBox | None:
        """
        通过 name 获取

        :param db:
        :param name:
        :return:
        """
        return await self.select_model_by_column(db, name=name)
    
    
    async def get(self, db: AsyncSession, pk: int) -> MailBox | None:
        """
        获取 MailBox

        :param db:
        :param pk:
        :return:
        """
        return await self.select_model(db, pk)

    async def get_list(self) -> Select:
        """
        获取邮箱列表

        :return:
        """
        return await self.select_order('created_time', 'desc')

    async def get_all(self, db: AsyncSession) -> Sequence[MailBox]:
        """
        获取所有 MailBox

        :param db:
        :return:
        """
        return await self.select_models(db)

    async def create(self, db: AsyncSession, obj_in: CreateMailBoxParam) -> None:
        """
        创建 MailBox

        :param db:
        :param obj_in:
        :return:
        """
        await self.create_model(db, obj_in)

    async def update(self, db: AsyncSession, pk: int, obj_in: UpdateMailBoxParam) -> int:
        """
        更新 MailBox

        :param db:
        :param pk:
        :param obj_in:
        :return:
        """
        return await self.update_model(db, pk, obj_in)

    async def delete(self, db: AsyncSession, pk: list[int]) -> int:
        """
        删除 MailBox

        :param db:
        :param pk:
        :return:
        """
        return  await self.delete_model_by_column(db, allow_multiple=True, id__in=pk)


mail_box_dao: CRUDMailBox = CRUDMailBox(MailBox)