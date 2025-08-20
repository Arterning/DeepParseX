#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from backend.app.admin.crud.crud_sys_subject_predict_object import sys_subject_predict_object_dao
from backend.app.admin.model.sys_subject_predict_object import SubjectPredictObject
from backend.app.admin.schema.subject_predict_object import CreateSubjectPredictObjectParam, UpdateSubjectPredictObjectParam
from backend.common.exception import errors
from backend.database.db_pg import async_db_session
from sqlalchemy import Select


class SubjectPredictObjectService:
    @staticmethod
    async def get(*, pk: int) -> SubjectPredictObject:
        async with async_db_session() as db:
            sys_subject_predict_object = await sys_subject_predict_object_dao.get(db, pk)
            if not sys_subject_predict_object:
                raise errors.NotFoundError(msg='不存在')
            return sys_subject_predict_object
    
    @staticmethod
    async def get_select() -> Select:
        return await sys_subject_predict_object_dao.get_list()

    @staticmethod
    async def get_all() -> Sequence[SubjectPredictObject]:
        async with async_db_session() as db:
            sys_subject_predict_objects = await sys_subject_predict_object_dao.get_all(db)
            return sys_subject_predict_objects

    @staticmethod
    async def create(*, obj: CreateSubjectPredictObjectParam) -> None:
        async with async_db_session.begin() as db:
            await sys_subject_predict_object_dao.create(db, obj)

    @staticmethod
    async def update(*, pk: int, obj: UpdateSubjectPredictObjectParam) -> int:
        async with async_db_session.begin() as db:
            count = await sys_subject_predict_object_dao.update(db, pk, obj)
            return count

    @staticmethod
    async def delete(*, pk: list[int]) -> int:
        async with async_db_session.begin() as db:
            count = await sys_subject_predict_object_dao.delete(db, pk)
            return count


sys_subject_predict_object_service = SubjectPredictObjectService()