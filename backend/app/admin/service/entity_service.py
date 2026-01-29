#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from typing import Sequence, Dict, List, Any

from backend.app.admin.crud.crud_entity import entity_dao
from backend.app.admin.crud.crud_entity_relationship import entity_relation_dao
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

    # 预设字段映射
    DEFAULT_EDITABLE_FIELDS = {
        '人物': ['性别', '国籍', '组织', '职位', '联系方式'],
        '组织': ['类型', '国家'],
        '事件': ['时间', '地点', '参与者']
    }

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

            # 获取关联文档内容
            if entity.docs:
                doc_contents = []
                for doc in entity.docs[:5]:  # 限制最多5个文档避免上下文过长
                    if doc.content:
                        # 截取前2000字符避免内容过长
                        content = doc.content[:2000] if len(doc.content) > 2000 else doc.content
                        doc_contents.append(f'[{doc.title}]: {content}')
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

                # 返回结果包含 properties 和 description
                return {'properties': properties, 'description': description}

            except json.JSONDecodeError as e:
                log.error(f'AI 响应解析失败: {ai_response}, 错误: {e}')
                raise errors.RequestError(msg='AI 响应格式错误，无法解析为JSON')
            except Exception as e:
                log.error(f'生成属性失败: {e}')
                raise errors.RequestError(msg=f'生成属性失败: {str(e)}')


entity_service = EntityService()