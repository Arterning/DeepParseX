#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy import Select,select, desc, and_, update
from sqlalchemy_crud_plus import CRUDPlus
from backend.app.admin.model import SysOrg, SysAssets, SysDoc
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.admin.schema.org import OrgParam, UpdateOrgParam
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
        
        where = []
        where.append(self.model.id == pk)
        res = await db.execute(
             select(self.model)
            .options(selectinload(self.model.docs))
            .options(selectinload(self.model.assets))
            .where(*where)
        )
        return res.scalars().first()


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
        org = await self.get(db, pk)

        for i in list(org.docs):
            org.docs.remove(i)
        doc_list = []
        for doc_id in obj.docs:
            doc_list.append(await db.get(SysDoc, doc_id))
        org.docs.extend(doc_list)

        for i in list(org.assets):
            org.assets.remove(i)
        a_list = []
        for a_id in obj.assets:
            a_list.append(await db.get(SysAssets, a_id))
        org.assets.extend(a_list)

        param = UpdateOrgParam(org_name=obj.org_name, org_desc=obj.org_desc,
                               org_assets_nums=len(obj.assets), org_file_nums=len(obj.docs))
        return await self.update_model(db,pk,param)
    

    async def delete(self, db: AsyncSession, pk:list[int]) -> int:
        """
        删除组织

        :param db:
        :
        :return:
        """
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pk)

org_dao: CRUDOrg = CRUDOrg(SysOrg)
