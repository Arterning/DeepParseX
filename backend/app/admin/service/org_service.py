#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy import Select
from pyexpat import errors
from backend.app.admin.crud.crud_org import org_dao
from backend.database.db_pg import async_db_session
from backend.app.admin.schema.org import OrgParam
from backend.app.admin.model.sys_org import SysOrg
from backend.common.exception import errors

class OrgService:

    @staticmethod
    async def get(*, pk: int) -> SysOrg:
        async with async_db_session() as db:
            org = await org_dao.get(db, pk)
            if not org:
                raise errors.NotFoundError(msg='组织不存在')
            return org
        
    @staticmethod
    async def get_select(*, name: str = None) -> Select:
        return await org_dao.get_list(name=name)
        
    @staticmethod
    async def get_all_orgs() -> list[SysOrg]:
        async with async_db_session() as db:
            org = await org_dao.get_all(db)
            if not org:
                raise errors.NotFoundError(msg='组织不存在')
            return org 
        
    @staticmethod
    async def create(*, obj: OrgParam) -> None:
        async with async_db_session.begin() as db:
            await org_dao.create(db, obj)

    @staticmethod
    async def update(*, pk:int,obj: OrgParam) -> None:
        async with async_db_session.begin() as db:
            return await org_dao.update(db,pk, obj)
        
    @staticmethod
    async def delete(*, pk:int) -> None:
        async with async_db_session.begin() as db:
            return await org_dao.delete(db,pk)
    

org_service = OrgService()
