#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from sqlalchemy import select,delete, Select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model.sys_person import Person
from backend.app.admin.model.sys_person_relation import PersonRelation
from backend.app.admin.schema.person import CreatePersonParam, UpdatePersonParam


class CRUDPerson(CRUDPlus[Person]):
    async def get(self, db: AsyncSession, pk: int) -> Person | None:
        """
        获取 Person

       
        :param db:
        :param pk:
        :return:
        """

        return await self.select_model(db, pk)
    
    async def get_by_ids(self, db: AsyncSession, ids: list[int]) -> Sequence[Person]:
        res = await db.execute(select(self.model).where(self.model.id.in_(ids)))
        return res.scalars().all()


    async def get_list(self) -> Select:
        """
        获取人物列表

        :return:
        """
        return await self.select_order('created_time', 'desc')

    async def get_all(self, db: AsyncSession) -> Sequence[Person]:
        """
        获取所有 Person

        :param db:
        :return:
        """
        return await self.select_models(db)

    async def create(self, db: AsyncSession, obj_in: CreatePersonParam) -> None:
        """
        创建 Person

        :param db:
        :param obj_in:
        :return:
        """
        await self.create_model(db, obj_in)

    async def update(self, db: AsyncSession, pk: int, obj_in: UpdatePersonParam) -> int:
        """
        更新 Person

        :param db:
        :param pk:
        :param obj_in:
        :return:
        """
        return await self.update_model(db, pk, obj_in)

    async def delete(self, db: AsyncSession, pk: list[int]) -> int:
        """
        删除 Person

        :param db:
        :param pk:
        :return:
        """
        return  await self.delete_model_by_column(db, allow_multiple=True, id__in=pk)

    
    async def get_relations(self, db: AsyncSession, center_person_id: int, degrees: int) -> list[PersonRelation]:
        sql = f"""
        WITH RECURSIVE graph_search AS (SELECT person_id, other_id, 1 AS degree, relation_type
                                FROM sys_person_relation
                                WHERE person_id = :center_person_id
                                   OR other_id = :center_person_id

                                UNION

                                SELECT r.person_id, r.other_id, gs.degree + 1, r.relation_type
                                FROM sys_person_relation r
                                         JOIN graph_search gs ON
                                            r.person_id = gs.other_id OR
                                            r.other_id = gs.person_id OR
                                            r.person_id = gs.person_id OR
                                            r.other_id = gs.other_id
                                WHERE gs.degree < :degrees)
SELECT DISTINCT person_id, other_id, relation_type
FROM graph_search
        """
        result = await db.execute(
            text(sql),
            {
                "center_person_id": center_person_id,
                "degrees": degrees
            }
        )
        subgraph = result.fetchall()
        return subgraph




person_dao: CRUDPerson = CRUDPerson(Person)