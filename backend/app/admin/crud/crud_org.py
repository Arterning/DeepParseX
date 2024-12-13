#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy import Select,select, desc, and_, update
from sqlalchemy_crud_plus import CRUDPlus
from backend.app.admin.model import SysOrg
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.admin.schema.org import OrgParam
from sqlalchemy.orm import selectinload

class CRUDOrg(CRUDPlus[SysOrg]):

    async def get_list(self, name: str = None) -> Select:
        where_list = []
        stmt = select(self.model).order_by(desc(self.model.created_time))
        if name is not None and name != '':
            where_list.append(self.model.org_name.like(f'%{name}%'))
        if where_list:
            stmt = stmt.where(and_(*where_list))
        return stmt


    async def get(self, db: AsyncSession, pk: int) -> SysOrg | None:
        """
        获取 Sysorg

        :param db:
        :param pk:
        :return:
        """
        
        return await self.select_model(db, pk)

    async def get_all(self, db: AsyncSession) -> list[SysOrg] | None:
        """
        获取 所有Sysorg
        :return:
        """
        
        return await self.select_models(db);

    async def create(self, db: AsyncSession, obj: OrgParam) -> None:
        """
        创建组织

        :param db:
        :param obj:
        :
        :return:
        """
        await self.create_model(db,obj)


    async def update(self, db: AsyncSession, pk:int,obj: OrgParam) -> int:
        """
        创建组织

        :param db:
        :param obj:
        :
        :return:
        """
        return await self.update_model(db,pk,obj)
    

    async def delete(self, db: AsyncSession, pk:int,) -> int:
        """
        删除组织

        :param db:
        :
        :return:
        """
        return await self.delete_model(db,pk)

org_dao: CRUDOrg = CRUDOrg(SysOrg)
