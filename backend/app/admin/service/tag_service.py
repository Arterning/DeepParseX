#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from sqlalchemy import Select, insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin.crud.crud_tag import tag_dao
from backend.app.admin.model.sys_tag import Tag
from backend.app.admin.model.sys_tag_doc import sys_tag_doc
from backend.app.admin.schema.tag import CreateTagParam, UpdateTagParam
from backend.common.exception import errors
from backend.common.log import log
from backend.database.db_pg import async_db_session


class TagService:
    @staticmethod
    async def get(*, pk: int) -> Tag:
        async with async_db_session() as db:
            tag = await tag_dao.get(db, pk)
            if not tag:
                raise errors.NotFoundError(msg='不存在')
            return tag
    
    @staticmethod
    async def get_select() -> Select:
        return await tag_dao.get_list()

    @staticmethod
    async def get_all() -> Sequence[Tag]:
        async with async_db_session() as db:
            tags = await tag_dao.get_all(db)
            return tags

    @staticmethod
    async def get_all_by_user(*, user_id: int, tag_type: str | None = None) -> Sequence[Tag]:
        """获取用户的所有标签（包括用户创建的标签和系统标签）"""
        async with async_db_session() as db:
            tags = await tag_dao.get_all_by_user(db, user_id, tag_type=tag_type)
            return tags

    @staticmethod
    async def create(*, obj: CreateTagParam) -> Tag:
        async with async_db_session.begin() as db:
            tag = await tag_dao.create(db, obj)
            return tag

    @staticmethod
    async def update(*, pk: int, obj: UpdateTagParam) -> int:
        async with async_db_session.begin() as db:
            count = await tag_dao.update(db, pk, obj)
            return count

    @staticmethod
    async def delete(*, pk: list[int]) -> int:
        async with async_db_session.begin() as db:
            count = await tag_dao.delete(db, pk)
            return count

    @staticmethod
    async def get_by_name(*, name: str) -> Tag | None:
        """根据名称获取标签"""
        async with async_db_session() as db:
            return await tag_dao.get_by_name(db, name)

    @staticmethod
    async def add_tags_to_doc(*, doc_id: int, tag_names: list[str]) -> list[Tag]:
        """
        为文档添加标签（系统自动打标签，create_user 为空）

        :param doc_id: 文档ID
        :param tag_names: 标签名称列表
        :return: 添加的标签列表
        """
        if not tag_names:
            return []

        added_tags = []
        async with async_db_session.begin() as db:
            for tag_name in tag_names:
                # 获取或创建标签（系统自动创建的标签不设置 create_user）
                tag = await tag_dao.get_or_create_by_name(db, tag_name)
                if tag:
                    # 检查是否已存在关联
                    from sqlalchemy import select
                    existing = await db.execute(
                        select(sys_tag_doc).where(
                            sys_tag_doc.c.tag_id == tag.id,
                            sys_tag_doc.c.doc_id == doc_id
                        )
                    )
                    if not existing.first():
                        # 创建关联
                        await db.execute(
                            insert(sys_tag_doc).values(tag_id=tag.id, doc_id=doc_id)
                        )
                        added_tags.append(tag)
                        log.info(f"文档 {doc_id} 添加标签: {tag_name}")
        return added_tags


tag_service = TagService()