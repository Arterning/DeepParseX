#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy import Select,select, desc, and_, update
from sqlalchemy_crud_plus import CRUDPlus
from backend.app.admin.model import SysAssets
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.admin.schema.assets import AssetsParam
from sqlalchemy.orm import selectinload


class CRUDOrg(CRUDPlus[SysAssets]):

    async def get_list(self, ip_addr:str = None, assets_name: str = None) -> Select:
        where_list = []
        stmt = select(self.model).order_by(desc(self.model.created_time))
        if assets_name is not None and assets_name != '':
            where_list.append(self.model.assets_name.like(f'%{assets_name}%'))
        if ip_addr is not None and ip_addr != '':
            where_list.append(self.model.ip_addr.like(f'%{ip_addr}%'))
        if where_list:
            stmt = stmt.where(and_(*where_list))
        return stmt

    async def get(self, db: AsyncSession, pk: int) -> SysAssets | None:
        """
        获取 Sysorg

        :param db:
        :param pk:
        :return:
        """
        
        return await self.select_model(db, pk)

    async def get_all(self, db: AsyncSession) -> list[SysAssets] | None:
        """
        获取 所有Sysorg
        :return:
        """
        
        return await self.select_models(db);

    async def create(self, db: AsyncSession, obj: AssetsParam) -> None:
        """
        创建组织

        :param db:
        :param obj:
        :
        :return:
        """
        await self.create_model(db,obj)
    
    async def bulk_create (self, db: AsyncSession, obj: list[AssetsParam]):
        """
        批量插入多个资产

        :param db: 数据库会话
        :param objs: 包含多个 AssetsParam 对象的列表
        :return: None
        """
        # 将 AssetsParam 对象转换为字典形式，便于批量插入
        data =[]
        for o in obj:
            o.model_dump()
            data.append(o)
        # data = [o.model_dump() for o in obj]
        await self.create_models(db,data,commit=True)


    async def update(self, db: AsyncSession, pk:int,obj: AssetsParam) -> int:
        """
        创建组织

        :param db:
        :param obj:
        :
        :return:
        """
        return await self.update_model(db,pk,obj)
    

    async def delete(self, db: AsyncSession, pk: list[int]) -> int:
        """
        删除组织

        :param db:
        :
        :return:
        """
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pk)

assets_dao: CRUDOrg = CRUDOrg(SysAssets)
