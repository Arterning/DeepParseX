#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from backend.app.admin.crud.crud_social_account import social_account_dao
from backend.app.admin.model.social_account import SocialAccount
from backend.app.admin.schema.social_account import CreateSocialAccountParam, UpdateSocialAccountParam
from backend.common.exception import errors
from backend.database.db_pg import async_db_session
from sqlalchemy import Select


class SocialAccountService:
    @staticmethod
    async def get(*, pk: int) -> SocialAccount:
        async with async_db_session() as db:
            social_account = await social_account_dao.get(db, pk)
            if not social_account:
                raise errors.NotFoundError(msg='不存在')
            return social_account
    
    @staticmethod
    async def get_select() -> Select:
        return await social_account_dao.get_list()

    @staticmethod
    async def get_all() -> Sequence[SocialAccount]:
        async with async_db_session() as db:
            social_accounts = await social_account_dao.get_all(db)
            return social_accounts

    @staticmethod
    async def create(*, obj: CreateSocialAccountParam) -> None:
        async with async_db_session.begin() as db:
            await social_account_dao.create(db, obj)

    @staticmethod
    async def update(*, pk: int, obj: UpdateSocialAccountParam) -> int:
        async with async_db_session.begin() as db:
            count = await social_account_dao.update(db, pk, obj)
            return count

    @staticmethod
    async def delete(*, pk: list[int]) -> int:
        async with async_db_session.begin() as db:
            count = await social_account_dao.delete(db, pk)
            return count


social_account_service = SocialAccountService()