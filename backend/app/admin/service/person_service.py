#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from backend.app.admin.crud.crud_person import person_dao
from backend.app.admin.model.sys_person import Person
from backend.app.admin.model.sys_person_relation import PersonRelation
from backend.app.admin.schema.person import CreatePersonParam, UpdatePersonParam
from backend.common.exception import errors
from backend.database.db_pg import async_db_session
from sqlalchemy import Select
import networkx as nx


class PersonService:
    @staticmethod
    async def get(*, pk: int) -> Person:
        async with async_db_session() as db:
            person = await person_dao.get(db, pk)
            if not person:
                raise errors.NotFoundError(msg='不存在')
            return person
        
    # 根据ids获取
    @staticmethod
    async def get_by_ids(*, ids: list[int]) -> Sequence[Person]:
        async with async_db_session() as db:
            persons = await person_dao.get_by_ids(db, ids)
            return persons
    
    @staticmethod
    async def get_select() -> Select:
        return await person_dao.get_list()

    @staticmethod
    async def get_all() -> Sequence[Person]:
        async with async_db_session() as db:
            persons = await person_dao.get_all(db)
            return persons

    @staticmethod
    async def create(*, obj: CreatePersonParam) -> None:
        async with async_db_session.begin() as db:
            await person_dao.create(db, obj)

    @staticmethod
    async def update(*, pk: int, obj: UpdatePersonParam) -> int:
        async with async_db_session.begin() as db:
            count = await person_dao.update(db, pk, obj)
            return count

    @staticmethod
    async def delete(*, pk: list[int]) -> int:
        async with async_db_session.begin() as db:
            count = await person_dao.delete(db, pk)
            return count

    @staticmethod
    async def get_relations(*, center_person_id: int, degrees=7) -> list[PersonRelation]:
         """
            获取以某个人为中心的n度关系
         """
         async with async_db_session.begin() as db:
             return await person_dao.get_relations(db, center_person_id, degrees)
         
    @staticmethod
    async def get_subgraph(*, center_person_id: int, degrees=7) -> list[PersonRelation]:
         """
            获取以某个人为中心的n度关系子图
         """
         async with async_db_session.begin() as db:
             relations = await person_dao.get_relations(db, center_person_id, degrees)
             person_ids = {p for edge in relations for p in edge}
             person_ids = list(person_ids)
            #  去掉person_ids中的非数字元素
             person_ids = [p for p in person_ids if isinstance(p, int)]
             persons = await person_dao.get_by_ids(db, person_ids)
            #  persons只需要保留id和name防止出现sqlalchemy.orm.exc.DetachedInstanceError:
             persons = [{"id": p.id, "name": p.name} for p in persons]

             graph = nx.DiGraph()
             for node in persons:
                graph.add_node(
                    node['id'],
                    **{k:v for k,v in node.items() if k != 'id'}
                )

             for source, target, relation_type in relations:
                if graph.has_edge(source, target):
                    continue
                # 这里可以添加更详细的关系属性
                graph.add_edge(source, target, relation_type=relation_type)
             return {"nodes": persons, "edges": relations, "graph": graph}

         


person_service = PersonService()