#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pyexpat import errors
from sqlalchemy import Select
from backend.app.admin.crud.crud_assets import assets_dao
from backend.database.db_pg import async_db_session
from backend.app.admin.schema.assets import AssetsParam
from backend.app.admin.model.sys_assets import SysAssets
from backend.common.exception import errors

class AssetsService:

    @staticmethod
    async def get_select(*, assets_name: str = None) -> Select:
        return await assets_dao.get_list(assets_name=assets_name)
    
    @staticmethod
    async def get(*, pk: int) -> SysAssets:
        async with async_db_session() as db:
            org = await assets_dao.get(db, pk)
            if not org:
                raise errors.NotFoundError(msg='资产不存在')
            return org
        
    @staticmethod
    async def get_all_assets() -> list[SysAssets]:
        async with async_db_session() as db:
            orgs = await assets_dao.get_all(db)
            return orgs
        
    @staticmethod
    async def create(*, obj: AssetsParam) -> None:
        async with async_db_session.begin() as db:
            await assets_dao.create(db, obj)
    
    @staticmethod
    async def bulk_create(*, obj: list[AssetsParam]) -> None:
        async with async_db_session.begin() as db:
            await assets_dao.bulk_create(db, obj)

    @staticmethod
    async def update(*, pk:int,obj: AssetsParam) -> None:
        async with async_db_session.begin() as db:
            return await assets_dao.update(db,pk, obj)
        
    @staticmethod
    async def delete(*, pk:list[int]) -> None:
        async with async_db_session.begin() as db:
            return await assets_dao.delete(db,pk)
    

assets_service = AssetsService()
