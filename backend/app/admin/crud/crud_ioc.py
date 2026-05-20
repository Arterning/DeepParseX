#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy import Select, select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model.sys_ioc import IocRecord
from backend.app.admin.schema.ioc import CreateIocParam, UpdateIocStatusParam


class CRUDIoc(CRUDPlus[IocRecord]):

    async def get(self, db: AsyncSession, pk: int) -> IocRecord | None:
        return await self.select_model(db, pk)

    async def get_by_doc_type_value(
        self, db: AsyncSession, doc_id: int | None, ioc_type: str, value: str
    ) -> IocRecord | None:
        stmt = select(self.model).where(
            self.model.doc_id == doc_id,
            self.model.ioc_type == ioc_type,
            self.model.value == value,
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_list(
        self,
        doc_id: int | None = None,
        ioc_type: str | None = None,
        value: str | None = None,
        status: int | None = None,
    ) -> Select:
        stmt = select(self.model).order_by(self.model.created_time.desc())
        if doc_id is not None:
            stmt = stmt.where(self.model.doc_id == doc_id)
        if ioc_type:
            stmt = stmt.where(self.model.ioc_type == ioc_type)
        if value:
            stmt = stmt.where(self.model.value.like(f'%{value}%'))
        if status is not None:
            stmt = stmt.where(self.model.status == status)
        return stmt

    async def create(self, db: AsyncSession, obj_in: CreateIocParam) -> IocRecord:
        return await self.create_model(db, obj_in)

    async def bulk_create(self, db: AsyncSession, objs: list[CreateIocParam]) -> int:
        """批量创建，跳过已存在的（依赖唯一约束 + on_conflict_do_nothing）"""
        from sqlalchemy.dialects.postgresql import insert
        from backend.utils.timezone import timezone
        if not objs:
            return 0
        now = timezone.now()
        rows = [{**obj.model_dump(), 'created_time': now} for obj in objs]
        stmt = insert(self.model).values(rows).on_conflict_do_nothing(
            constraint='uq_ioc_doc_type_value'
        )
        result = await db.execute(stmt)
        return result.rowcount

    async def update_status(self, db: AsyncSession, pk: int, obj_in: UpdateIocStatusParam) -> int:
        return await self.update_model(db, pk, obj_in)

    async def update_entity_id(self, db: AsyncSession, pk: int, entity_id: int) -> int:
        return await self.update_model(db, pk, {'entity_id': entity_id, 'status': 1})

    async def delete(self, db: AsyncSession, pk: list[int]) -> int:
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pk)

    async def delete_by_doc(self, db: AsyncSession, doc_id: int) -> int:
        result = await db.execute(
            delete(self.model).where(self.model.doc_id == doc_id)
        )
        return result.rowcount


ioc_dao: CRUDIoc = CRUDIoc(IocRecord)
