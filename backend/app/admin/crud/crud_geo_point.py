#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy import Select, select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model.sys_geo_point import GeoPoint
from backend.app.admin.schema.geo_point import CreateGeoPointParam


class CRUDGeoPoint(CRUDPlus[GeoPoint]):

    async def get(self, db: AsyncSession, pk: int) -> GeoPoint | None:
        return await self.select_model(db, pk)

    async def get_list(
        self,
        doc_id: int | None = None,
        ioc_id: int | None = None,
        source_type: str | None = None,
    ) -> Select:
        stmt = select(self.model).order_by(self.model.created_time.desc())
        if doc_id is not None:
            stmt = stmt.where(self.model.doc_id == doc_id)
        if ioc_id is not None:
            stmt = stmt.where(self.model.ioc_id == ioc_id)
        if source_type:
            stmt = stmt.where(self.model.source_type == source_type)
        return stmt

    async def get_all_with_coords(self, db: AsyncSession) -> list[GeoPoint]:
        """获取所有有坐标的点，供地图展示"""
        result = await db.execute(
            select(self.model)
            .where(self.model.lat.is_not(None), self.model.lng.is_not(None))
            .order_by(self.model.created_time.desc())
        )
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, obj_in: CreateGeoPointParam) -> GeoPoint:
        return await self.create_model(db, obj_in)

    async def get_by_doc(self, db: AsyncSession, doc_id: int) -> GeoPoint | None:
        result = await db.execute(
            select(self.model).where(
                self.model.doc_id == doc_id,
                self.model.source_type == 'exif',
            )
        )
        return result.scalars().first()

    async def get_by_ioc(self, db: AsyncSession, ioc_id: int) -> GeoPoint | None:
        result = await db.execute(
            select(self.model).where(self.model.ioc_id == ioc_id)
        )
        return result.scalars().first()

    async def delete_by_doc(self, db: AsyncSession, doc_id: int) -> int:
        result = await db.execute(
            delete(self.model).where(self.model.doc_id == doc_id)
        )
        return result.rowcount

    async def delete(self, db: AsyncSession, pk: list[int]) -> int:
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pk)


geo_point_dao: CRUDGeoPoint = CRUDGeoPoint(GeoPoint)
