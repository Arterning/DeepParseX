#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from backend.app.admin.crud.crud_subject import subject_dao
from backend.app.admin.model.sys_subject import Subject
from backend.app.admin.schema.subject import CreateSubjectParam, UpdateSubjectParam
from backend.common.exception import errors
from backend.database.db_pg import async_db_session
from sqlalchemy import Select


class SubjectService:
    @staticmethod
    async def get(*, pk: int) -> Subject:
        async with async_db_session() as db:
            subject = await subject_dao.get(db, pk)
            if not subject:
                raise errors.NotFoundError(msg='不存在')
            return subject
    
    @staticmethod
    async def get_select() -> Select:
        return await subject_dao.get_list()

    @staticmethod
    async def get_all() -> Sequence[Subject]:
        async with async_db_session() as db:
            subjects = await subject_dao.get_all(db)
            return subjects

    @staticmethod
    async def create(*, obj: CreateSubjectParam) -> None:
        async with async_db_session.begin() as db:
            await subject_dao.create(db, obj)

    @staticmethod
    async def update(*, pk: int, obj: UpdateSubjectParam) -> int:
        async with async_db_session.begin() as db:
            count = await subject_dao.update(db, pk, obj)
            return count

    @staticmethod
    async def delete(*, pk: list[int]) -> int:
        async with async_db_session.begin() as db:
            count = await subject_dao.delete(db, pk)
            return count


subject_service = SubjectService()