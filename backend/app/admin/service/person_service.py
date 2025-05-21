#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from backend.app.admin.crud.crud_person import person_dao
from backend.app.admin.crud.crud_person_relation import person_relation_dao
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
    async def get_relation_graph_data(*, center_person_id: int, degrees=7) -> dict:
         """
            获取以某个人为中心的n度关系
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
             edges = [{"source": r.person_id, "target": r.other_id, "relation_type": r.relation_type} for r in relations]

             return {"nodes": persons, "edges": edges}
     

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
             return graph

         

    @staticmethod
    async def get_full_graph():
        async with async_db_session.begin() as db:
            persons = await person_dao.get_all(db)
            relationships = await person_relation_dao.get_all(db)

            persons = [{"id": p.id, "name": p.name} for p in persons]
            relationships = [{"source": r.person_id, "target": r.other_id, "relation_type": r.relation_type} for r in relationships]

            graph = nx.DiGraph()
            for node in persons:
                graph.add_node(
                    node['id'],
                    **{k:v for k,v in node.items() if k != 'id'}
                )

            # 添加边
            for rel in relationships:
                source = rel['source']
                target = rel['target']
                if graph.has_edge(source, target):
                    continue
                graph.add_edge(
                    source,
                    target,
                    **{k:v for k,v in rel.items()
                    if k not in ('source', 'target')}
                )

            return {"nodes": persons, "edges": relationships, "graph": graph}


    @staticmethod
    def find_shortest_path(*, person1_id :int, person2_id :int, graph: nx.DiGraph):
        """查找两人之间的最短路径"""
        try:
            path = nx.shortest_path(graph, person1_id, person2_id)
            return {
                "path": path,
                "length": len(path)-1,
                "nodes": [graph.nodes[node_id] for node_id in path]
            }
        except nx.NetworkXNoPath:
            return None

    @staticmethod
    def analyze_network(*, graph: nx.DiGraph, person_id):
        """分析个人网络特征"""
        if person_id not in graph:
            return None

        return {
            "degree_centrality": nx.degree_centrality(graph).get(person_id),
            "betweenness": nx.betweenness_centrality(graph).get(person_id),
            "closeness": nx.closeness_centrality(graph).get(person_id),
            "pagerank": nx.pagerank(graph).get(person_id)
        }


    @staticmethod
    def find_common_connections(*, graph: nx.DiGraph,  person1_id, person2_id):
        """查找共同联系人"""
        neighbors1 = set(graph.successors(person1_id))
        neighbors2 = set(graph.successors(person2_id))
        common = neighbors1 & neighbors2

        return {
            "common_connections": list(common),
            "count": len(common)
        }
    

person_service = PersonService()