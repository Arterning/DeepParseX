#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from backend.app.admin.crud.crud_social_account_post import social_account_post_dao
from backend.app.admin.model.social_account_post import SocialAccountPost
from backend.app.admin.schema.social_account_post import CreateSocialAccountPostParam, UpdateSocialAccountPostParam
from backend.common.exception import errors
from backend.database.db_pg import async_db_session
from sqlalchemy import Select


class SocialAccountPostService:
    @staticmethod
    async def get(*, pk: int) -> SocialAccountPost:
        async with async_db_session() as db:
            social_account_post = await social_account_post_dao.get(db, pk)
            if not social_account_post:
                raise errors.NotFoundError(msg='不存在')
            return social_account_post
    
    @staticmethod
    async def get_select() -> Select:
        return await social_account_post_dao.get_list()

    @staticmethod
    async def get_all() -> Sequence[SocialAccountPost]:
        async with async_db_session() as db:
            social_account_posts = await social_account_post_dao.get_all(db)
            return social_account_posts

    @staticmethod
    async def create(*, obj: CreateSocialAccountPostParam) -> None:
        async with async_db_session.begin() as db:
            await social_account_post_dao.create(db, obj)

    @staticmethod
    async def update(*, pk: int, obj: UpdateSocialAccountPostParam) -> int:
        async with async_db_session.begin() as db:
            count = await social_account_post_dao.update(db, pk, obj)
            return count

    @staticmethod
    async def delete(*, pk: list[int]) -> int:
        async with async_db_session.begin() as db:
            count = await social_account_post_dao.delete(db, pk)
            return count


social_account_post_service = SocialAccountPostService()