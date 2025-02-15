#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from sqlalchemy import delete, Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model.social_account_post import SocialAccountPost
from backend.app.admin.schema.social_account_post import CreateSocialAccountPostParam, UpdateSocialAccountPostParam


class CRUDSocialAccountPost(CRUDPlus[SocialAccountPost]):
    async def get(self, db: AsyncSession, pk: int) -> SocialAccountPost | None:
        """
        获取 SocialAccountPost

        :param db:
        :param pk:
        :return:
        """
        return await self.select_model(db, pk)

    async def get_list(self) -> Select:
        """
        获取社交帖子列表

        :return:
        """
        return await self.select_order('created_time', 'desc')

    async def get_all(self, db: AsyncSession) -> Sequence[SocialAccountPost]:
        """
        获取所有 SocialAccountPost

        :param db:
        :return:
        """
        return await self.select_models(db)

    async def create(self, db: AsyncSession, obj_in: CreateSocialAccountPostParam) -> None:
        """
        创建 SocialAccountPost

        :param db:
        :param obj_in:
        :return:
        """
        await self.create_model(db, obj_in)

    async def update(self, db: AsyncSession, pk: int, obj_in: UpdateSocialAccountPostParam) -> int:
        """
        更新 SocialAccountPost

        :param db:
        :param pk:
        :param obj_in:
        :return:
        """
        return await self.update_model(db, pk, obj_in)

    async def delete(self, db: AsyncSession, pk: list[int]) -> int:
        """
        删除 SocialAccountPost

        :param db:
        :param pk:
        :return:
        """
        return  await self.delete_model_by_column(db, allow_multiple=True, id__in=pk)


social_account_post_dao: CRUDSocialAccountPost = CRUDSocialAccountPost(SocialAccountPost)