#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence, Dict, List

from backend.app.admin.crud.crud_entity import entity_dao
from backend.app.admin.crud.crud_entity_relationship import entity_relation_dao
from backend.app.admin.model.sys_entity import Entity
from backend.app.admin.model.sys_entity_relationship import EntityRelation
from backend.app.admin.schema.entity import CreateEntityParam, UpdateEntityParam
from backend.common.exception import errors
from backend.database.db_pg import async_db_session
from sqlalchemy import Select


class EntityService:
    @staticmethod
    async def get(*, pk: int) -> Entity:
        async with async_db_session() as db:
            entity = await entity_dao.get(db, pk)
            if not entity:
                raise errors.NotFoundError(msg='不存在')
            return entity
    
    @staticmethod
    async def get_entity_relationships(*, entity_id: int) -> List[Dict]:
        """
        获取指定实体ID的所有关系
        
        :param entity_id:
        :return:
        """
        async with async_db_session() as db:
            relationships = await entity_relation_dao.get_by_entity_id(db, entity_id)
            
            # 获取相关实体的信息
            entity_ids = set()
            for relation in relationships:
                if relation.source_id:
                    entity_ids.add(relation.source_id)
                if relation.target_id:
                    entity_ids.add(relation.target_id)
            
            # 移除当前实体ID，避免重复查询
            if entity_id in entity_ids:
                entity_ids.remove(entity_id)
            
            # 查询相关实体信息
            entities_dict = {}
            if entity_ids:
                stmt = Select(Entity).where(Entity.id.in_(entity_ids))
                result = await db.execute(stmt)
                entities = result.scalars().all()
                entities_dict = {e.id: e for e in entities}
            
            # 格式化关系数据
            formatted_relationships = []
            for relation in relationships:
                is_source = relation.source_id == entity_id
                related_entity_id = relation.target_id if is_source else relation.source_id
                related_entity = entities_dict.get(related_entity_id)
                
                formatted_relationships.append({
                    'id': relation.id,
                    'relation_type': relation.relation_type,
                    'weight': relation.weight,
                    'description': relation.description,
                    'direction': 'outgoing' if is_source else 'incoming',
                    'related_entity': {
                        'id': related_entity_id,
                        'name': related_entity.name if related_entity else None,
                        'entity_type': related_entity.entity_type if related_entity else None
                    }
                })
            
            return formatted_relationships
    
    @staticmethod
    async def get_select(name: str | None = None, entity_type: str | list[str] | None = None) -> Select:
        return await entity_dao.get_list(name=name, entity_type=entity_type)

    @staticmethod
    async def get_all() -> Sequence[Entity]:
        async with async_db_session() as db:
            entitys = await entity_dao.get_all(db)
            return entitys

    @staticmethod
    async def create(*, obj: CreateEntityParam) -> None:
        async with async_db_session.begin() as db:
            await entity_dao.create(db, obj)

    @staticmethod
    async def update(*, pk: int, obj: UpdateEntityParam) -> int:
        async with async_db_session.begin() as db:
            count = await entity_dao.update(db, pk, obj)
            return count

    @staticmethod
    async def delete(*, pk: list[int]) -> int:
        async with async_db_session.begin() as db:
            count = await entity_dao.delete(db, pk)
            return count


entity_service = EntityService()