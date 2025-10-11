#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Any

from backend.app.admin.crud.crud_doc_dir import doc_dir_dao
from backend.app.admin.model import SysDocDir
from backend.app.admin.schema.doc_dir import CreateDocDirParam, UpdateDocDirParam
from backend.common.exception import errors
from backend.database.db_pg import async_db_session
from backend.utils.build_tree import get_tree_data


class DocDirService:
    @staticmethod
    async def get(*, pk: int) -> SysDocDir:
        async with async_db_session() as db:
            doc_dir = await doc_dir_dao.get(db, pk)
            if not doc_dir:
                raise errors.NotFoundError(msg='目录不存在')
            return doc_dir

    @staticmethod
    async def get_doc_dir_tree(*, name: str | None = None) -> list[dict[str, Any]]:
        async with async_db_session() as db:
            doc_dir_select = await doc_dir_dao.get_all(db=db, name=name)
            tree_data = get_tree_data(doc_dir_select)
            return tree_data

    @staticmethod
    async def create(*, obj: CreateDocDirParam) -> None:
        async with async_db_session.begin() as db:
            # 检查是否存在相同名称和父级目录的记录
            doc_dir = await doc_dir_dao.get_by_name(db, obj.name, obj.parent_id)
            if doc_dir:
                raise errors.ForbiddenError(msg='目录名称已存在')
            # 验证父级目录是否存在
            if obj.parent_id:
                parent_dir = await doc_dir_dao.get(db, obj.parent_id)
                if not parent_dir:
                    raise errors.NotFoundError(msg='父级目录不存在')
            await doc_dir_dao.create(db, obj)

    @staticmethod
    async def update(*, pk: int, obj: UpdateDocDirParam) -> int:
        async with async_db_session.begin() as db:
            doc_dir = await doc_dir_dao.get(db, pk)
            if not doc_dir:
                raise errors.NotFoundError(msg='目录不存在')
            if doc_dir.name != obj.name:
                # 检查是否存在相同名称和父级目录的记录
                if await doc_dir_dao.get_by_name(db, obj.name, obj.parent_id if obj.parent_id is not None else doc_dir.parent_id):
                    raise errors.ForbiddenError(msg='目录名称已存在')
            if obj.parent_id:
                parent_dir = await doc_dir_dao.get(db, obj.parent_id)
                if not parent_dir:
                    raise errors.NotFoundError(msg='父级目录不存在')
            if obj.parent_id == doc_dir.id:
                raise errors.ForbiddenError(msg='禁止关联自身为父级')
            count = await doc_dir_dao.update(db, pk, obj)
            return count

    @staticmethod
    async def delete(*, pk: int) -> int:
        async with async_db_session.begin() as db:
            docs_in_dir = await doc_dir_dao.get_with_relation(db, pk)
            if docs_in_dir:
                raise errors.ForbiddenError(msg='目录下存在文件，无法删除')
            children = await doc_dir_dao.get_children(db, pk)
            if children:
                raise errors.ForbiddenError(msg='目录下存在子目录，无法删除')
            count = await doc_dir_dao.delete(db, pk)
            return count


doc_dir_service = DocDirService()
