#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from typing import Sequence, Dict, List, Any

from backend.app.admin.crud.crud_entity import entity_dao
from backend.app.admin.crud.crud_entity_relationship import entity_relation_dao
from backend.app.admin.crud.crud_star_collect import star_collect_dao
from backend.app.admin.model.sys_entity import Entity
from backend.app.admin.model.sys_entity_relationship import EntityRelation
from backend.app.admin.schema.entity import CreateEntityParam, UpdateEntityParam
from backend.app.admin.service.llm_service import llm_service
from backend.common.exception import errors
from backend.common.log import log
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
    async def analyze_entities(*, entity_ids: List[int]) -> Dict[str, Any]:
        """
        分析多个实体之间的关系，返回图谱数据

        :param entity_ids: 要分析的实体ID列表
        :return: { nodes: [...], edges: [...] }
        """
        async with async_db_session() as db:
            # 获取所有相关关系
            relationships = await entity_relation_dao.get_by_entity_ids(db, entity_ids)

            # 收集所有涉及的实体 ID（选中的 + 关系中发现的）
            all_entity_ids = set(entity_ids)
            for rel in relationships:
                if rel.source_id:
                    all_entity_ids.add(rel.source_id)
                if rel.target_id:
                    all_entity_ids.add(rel.target_id)

            # 一次性查询所有实体信息
            entities_dict: Dict[int, Entity] = {}
            if all_entity_ids:
                stmt = Select(Entity).where(Entity.id.in_(all_entity_ids))
                result = await db.execute(stmt)
                entities = result.scalars().all()
                entities_dict = {e.id: e for e in entities}

            selected_ids_set = set(entity_ids)

            # 构建 nodes
            nodes = []
            for eid, entity in entities_dict.items():
                nodes.append({
                    'id': eid,
                    'name': entity.name,
                    'entity_type': entity.entity_type,
                    'is_selected': eid in selected_ids_set,
                })

            # 构建 edges
            edges = []
            for rel in relationships:
                edges.append({
                    'id': rel.id,
                    'source_id': rel.source_id,
                    'target_id': rel.target_id,
                    'relation_type': rel.relation_type,
                    'weight': rel.weight,
                    'description': rel.description,
                })

            return {'nodes': nodes, 'edges': edges}

    @staticmethod
    async def get_select(name: str | None = None, entity_type: str | list[str] | None = None, eml: bool | None = None) -> Select:
        return await entity_dao.get_list(name=name, entity_type=entity_type, eml=eml)

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

    @staticmethod
    async def add_to_star(*, entity_id: int, star_id: int, created_by: int | None = None) -> bool:
        """
        将实体添加到收藏夹

        :param entity_id: 实体ID
        :param star_id: 收藏夹ID
        :param created_by: 创建人ID
        :return: 是否成功
        """
        async with async_db_session.begin() as db:
            # 检查实体是否存在
            entity = await entity_dao.get(db, entity_id)
            if not entity:
                raise errors.NotFoundError(msg='实体不存在')

            # 检查收藏夹是否存在
            star_collect = await star_collect_dao.get(db, star_id)
            if not star_collect:
                raise errors.NotFoundError(msg='收藏夹不存在')

            return await star_collect_dao.add_entity(db, star_id, entity_id, created_by)

    @staticmethod
    async def remove_from_star(*, entity_id: int, star_id: int) -> bool:
        """
        从收藏夹移除实体

        :param entity_id: 实体ID
        :param star_id: 收藏夹ID
        :return: 是否成功
        """
        async with async_db_session.begin() as db:
            return await star_collect_dao.remove_entity(db, star_id, entity_id)

    @staticmethod
    async def get_starred_ids(*, entity_id: int) -> list[int]:
        """
        获取实体所在的所有收藏夹ID列表

        :param entity_id: 实体ID
        :return: 收藏夹ID列表
        """
        async with async_db_session() as db:
            return await star_collect_dao.get_entity_starred_ids(db, entity_id)

    # 预设字段映射
    DEFAULT_EDITABLE_FIELDS = {
        '人物': ['性别', '国籍', '组织', '职位', '联系方式'],
        '组织': ['类型', '国家'],
        '事件': ['时间', '地点', '参与者']
    }

    @staticmethod
    async def _get_related_doc_contents(db, entity) -> tuple[list[str], list[int]]:
        """
        获取实体相关文档内容（全文检索命中的 chunk_text）

        :param db: 数据库会话
        :param entity: 实体对象
        :return: (格式化的文档内容列表, 尚未建立关联的doc_id列表)
        """
        from backend.app.admin.crud.crud_doc_chunk import sys_doc_chunk_dao

        # 已关联的 doc_id 集合（仅用于判断是否需要新建关联）
        existing_doc_ids = {doc.id for doc in entity.docs} if entity.docs else set()

        # 全文检索包含实体名称的文档，直接使用命中的 chunk_text
        search_results = await sys_doc_chunk_dao.search_doc_ids_by_keyword(
            db, entity.name, limit=20
        )

        # 保存检索结果到实体的 matched_chunks 字段
        entity.matched_chunks = search_results

        # 格式化内容 & 识别新文档
        doc_contents = []
        new_doc_ids = []
        for doc_info in search_results:
            chunks_text = '\n'.join(doc_info['chunks'])
            doc_contents.append(f'[{doc_info["doc_title"]}]: {chunks_text}')
            if doc_info['doc_id'] not in existing_doc_ids:
                new_doc_ids.append(doc_info['doc_id'])

        return doc_contents, new_doc_ids

    @staticmethod
    async def generate_properties_by_ai(*, pk: int) -> Dict[str, Any]:
        """
        根据实体类型调用 AI 生成实体属性

        :param pk: 实体ID
        :return: 生成的属性字典
        """
        from backend.app.admin.crud.crud_entity_type import entity_type_dao
        from sqlalchemy import select
        from backend.app.admin.model.sys_entity_type import EntityType

        async with async_db_session.begin() as db:
            # 获取实体（包含关联文档）
            entity = await entity_dao.get(db, pk)
            if not entity:
                raise errors.NotFoundError(msg='实体不存在')

            # 获取预设字段
            default_fields = EntityService.DEFAULT_EDITABLE_FIELDS.get(entity.entity_type, [])

            # 从数据库读取用户配置的字段
            custom_fields = []
            stmt = select(EntityType).where(EntityType.name == entity.entity_type)
            result = await db.execute(stmt)
            entity_type_obj = result.scalar_one_or_none()

            if entity_type_obj and entity_type_obj.field_definition:
                custom_fields = entity_type_obj.field_definition

            # 合并字段并去重（保持顺序）
            all_fields = []
            seen = set()
            for field in default_fields + custom_fields:
                if field not in seen:
                    all_fields.append(field)
                    seen.add(field)

            if not all_fields:
                raise errors.RequestError(
                    msg=f'实体类型 {entity.entity_type} 没有配置任何字段'
                )

            # 构建字段的 JSON 模板（字段名为中文）
            json_template_fields = [f'    "{field}": "字段值"' for field in all_fields]
            json_template_fields.append('    "描述": "实体简要描述（一两句话概括关键信息）"')
            json_template = '{\n' + ',\n'.join(json_template_fields) + '\n}'

            # 构建上下文信息
            context_parts = []
            context_parts.append(f'实体名称: {entity.name}')
            context_parts.append(f'实体类型: {entity.entity_type}')
            if entity.description:
                context_parts.append(f'现有描述: {entity.description}')

            # 获取关联文档内容（直接关联 + 全文检索）
            doc_contents, new_doc_ids = await EntityService._get_related_doc_contents(db, entity)
            if doc_contents:
                context_parts.append('关联文档内容:\n' + '\n'.join(doc_contents))

            user_input = '\n'.join(context_parts)

            # 构建 system prompt
            system_prompt = f'''你是一个信息提取专家。根据提供的实体信息和相关文档内容，提取{entity.entity_type}的属性信息。

请严格按照以下JSON格式输出，只输出JSON，不要有其他内容：
{json_template}

注意：
1. 如果某个属性无法从提供的信息中推断出来，请填写"未知"
2. 只输出JSON格式，不要有任何其他文字说明
3. 确保输出是有效的JSON格式
4. "描述" 字段必须填写，用于简要描述此{entity.entity_type}的关键信息
5. JSON的key必须使用中文，严格按照上述模板中的字段名'''

            try:
                # 调用 AI 服务
                ai_response = await llm_service.get_llm_response(system_prompt, user_input)
                log.info(f'AI 响应: {ai_response}')

                # 解析 JSON
                # 尝试从响应中提取 JSON
                response_text = ai_response.strip()
                # 如果响应被包裹在 markdown 代码块中，提取出来
                if response_text.startswith('```'):
                    lines = response_text.split('\n')
                    json_lines = []
                    in_json = False
                    for line in lines:
                        if line.startswith('```') and not in_json:
                            in_json = True
                            continue
                        elif line.startswith('```') and in_json:
                            break
                        elif in_json:
                            json_lines.append(line)
                    response_text = '\n'.join(json_lines)

                result = json.loads(response_text)

                # 提取 "描述" 字段
                description = result.pop('描述', None)

                # 剩余的作为 properties
                properties = result

                # 更新实体的 properties 和 description 字段
                await entity_dao.update_properties(db, pk, properties, description)

                # 为全文检索新发现的文档创建关联
                if new_doc_ids:
                    from backend.app.admin.model.sys_entity_doc import sys_entity_doc
                    for doc_id in new_doc_ids:
                        existing = await db.execute(
                            select(sys_entity_doc).where(
                                sys_entity_doc.c.entity_id == pk,
                                sys_entity_doc.c.doc_id == doc_id
                            )
                        )
                        if not existing.first():
                            await db.execute(
                                sys_entity_doc.insert().values(entity_id=pk, doc_id=doc_id)
                            )

                # 返回结果包含 properties 和 description
                return {'properties': properties, 'description': description}

            except json.JSONDecodeError as e:
                log.error(f'AI 响应解析失败: {ai_response}, 错误: {e}')
                raise errors.RequestError(msg='AI 响应格式错误，无法解析为JSON')
            except Exception as e:
                log.error(f'生成属性失败: {e}')
                raise errors.RequestError(msg=f'生成属性失败: {str(e)}')


    @staticmethod
    async def auto_link_and_generate_properties():
        """定时任务：自动为在文档中出现但未建立关联的实体生成属性

        查找实体名称在 sys_doc_chunk 表中出现但 sys_entity_doc 中未建立关联的实体，
        每次处理10个，调用 generate_properties_by_ai 方法。
        """
        from sqlalchemy import select, exists, func, or_
        from backend.app.admin.model.sys_doc_chunk import SysDocChunk
        from backend.app.admin.model.sys_entity_doc import sys_entity_doc

        try:
            async with async_db_session() as db:
                # 子查询：实体已关联的文档ID
                linked_docs = (
                    select(sys_entity_doc.c.doc_id)
                    .where(sys_entity_doc.c.entity_id == Entity.id)
                    .correlate(Entity)
                )

                # 条件：通过 chunk_vector (GIN索引) 全文检索实体名称，且该文档未与实体建立关联
                has_unlinked_mention = exists(
                    select(SysDocChunk.id).where(
                        SysDocChunk.chunk_vector.op('@@')(
                            func.plainto_tsquery('simple', func.lower(Entity.name))
                        ),
                        SysDocChunk.doc_id.notin_(linked_docs)
                    ).correlate(Entity)
                )

                stmt = (
                    select(Entity.id)
                    .where(Entity.name.isnot(None))
                    .where(func.length(Entity.name) >= 2)
                    .where(or_(has_unlinked_mention, Entity.matched_chunks.is_(None)))
                    .limit(10)
                )

                result = await db.execute(stmt)
                entity_ids = [row[0] for row in result.all()]

            if not entity_ids:
                log.info("没有需要处理的未关联实体")
                return

            log.info(f"开始为 {len(entity_ids)} 个未关联实体生成属性")

            success_count = 0
            error_count = 0

            for entity_id in entity_ids:
                try:
                    await EntityService.generate_properties_by_ai(pk=entity_id)
                    success_count += 1
                    log.info(f"实体 {entity_id} 属性生成完成")
                except Exception as e:
                    error_count += 1
                    log.error(f"实体 {entity_id} 属性生成失败: {str(e)}")

            log.info(f"未关联实体属性生成完成: 成功 {success_count} 个，失败 {error_count} 个")

        except Exception as e:
            log.error(f"自动处理未关联实体任务失败: {str(e)}")


entity_service = EntityService()