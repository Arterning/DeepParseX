#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import io
import json
import os

import jieba
import pandas as pd
from typing import Sequence, Dict, List, Any

from backend.app.admin.crud.crud_entity import entity_dao
from backend.app.admin.crud.crud_entity_relationship import entity_relation_dao
from backend.app.admin.crud.crud_star_collect import star_collect_dao
from backend.app.admin.model.sys_entity import Entity
from backend.app.admin.model.sys_entity_relationship import EntityRelation
from backend.app.admin.schema.entity import (
    BatchImportParam,
    CreateEntityParam,
    UpdateEntityParam,
)
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
    async def extract_relationships(*, pk: int) -> list[dict]:
        """
        为指定实体 AI 提取关系并持久化（即使已有关系也重新提取）

        :param pk: 实体 ID
        :return: 新提取的关系列表
        """
        async with async_db_session.begin() as db:
            entity = await entity_dao.get(db, pk)
            if not entity:
                raise errors.NotFoundError(msg='实体不存在')

            search_results = await EntityService._search_docs_by_name(db, entity.name)
            if not search_results:
                return []

            extracted = await EntityService._ai_extract_relationships(
                entity.name, entity.entity_type, search_results
            )

            from backend.common.context import get_current_user
            current_user = get_current_user()
            creator_id = current_user.id if current_user else None

            seen_rels: set[tuple] = set()
            new_rels = []
            for rel_data in extracted:
                target_name = (rel_data.get('target_name') or '').strip()
                relation_type = (rel_data.get('relation_type') or '').strip()
                if not target_name or target_name == entity.name:
                    continue
                key = (target_name, relation_type)
                if key in seen_rels:
                    continue
                seen_rels.add(key)

                result = await db.execute(
                    Select(Entity).where(Entity.name == target_name).limit(1)
                )
                target_entity = result.scalars().first()
                if not target_entity:
                    target_entity = Entity(
                        name=target_name,
                        entity_type=(rel_data.get('target_type') or None),
                        create_user=creator_id,
                    )
                    db.add(target_entity)
                    await db.flush()

                db.add(EntityRelation(
                    source_id=pk,
                    target_id=target_entity.id,
                    relation_type=relation_type or None,
                    description=(rel_data.get('description') or None),
                    weight=int(rel_data.get('weight') or 0),
                ))
                new_rels.append({
                    'target_name': target_name,
                    'relation_type': relation_type,
                })

            await db.flush()
            return new_rels

    @staticmethod
    async def analyze_entities(*, entity_ids: List[int]) -> Dict[str, Any]:
        """
        分析多个实体之间的关系，返回图谱数据。
        若某实体尚无任何关系，则自动通过文档检索 + AI 提取关系并持久化。

        :param entity_ids: 要分析的实体ID列表
        :return: { nodes: [...], edges: [...] }
        """
        async with async_db_session.begin() as db:
            # 获取已有关系
            relationships = await entity_relation_dao.get_by_entity_ids(db, entity_ids)

            # 判断哪些实体目前没有任何关系
            has_relation_ids: set[int] = set()
            for rel in relationships:
                if rel.source_id:
                    has_relation_ids.add(rel.source_id)
                if rel.target_id:
                    has_relation_ids.add(rel.target_id)
            no_relation_ids = [eid for eid in entity_ids if eid not in has_relation_ids]

            # 对无关系实体：搜索文档 → AI 提取 → 持久化
            if no_relation_ids:
                from backend.common.context import get_current_user
                current_user = get_current_user()
                creator_id = current_user.id if current_user else None

                for entity_id in no_relation_ids:
                    entity = await entity_dao.get(db, entity_id)
                    if not entity:
                        continue

                    search_results = await EntityService._search_docs_by_name(db, entity.name)
                    if not search_results:
                        continue

                    extracted = await EntityService._ai_extract_relationships(
                        entity.name, entity.entity_type, search_results
                    )

                    seen_rels: set[tuple] = set()
                    for rel_data in extracted:
                        target_name = (rel_data.get('target_name') or '').strip()
                        relation_type = (rel_data.get('relation_type') or '').strip()
                        if not target_name or target_name == entity.name:
                            continue
                        key = (target_name, relation_type)
                        if key in seen_rels:
                            continue
                        seen_rels.add(key)

                        # 查找或创建 target 实体
                        target_result = await db.execute(
                            Select(Entity).where(Entity.name == target_name).limit(1)
                        )
                        target_entity = target_result.scalars().first()
                        if not target_entity:
                            target_entity = Entity(
                                name=target_name,
                                entity_type=(rel_data.get('target_type') or None),
                                create_user=creator_id,
                            )
                            db.add(target_entity)
                            await db.flush()

                        db.add(EntityRelation(
                            source_id=entity_id,
                            target_id=target_entity.id,
                            relation_type=relation_type or None,
                            description=(rel_data.get('description') or None),
                            weight=int(rel_data.get('weight') or 0),
                        ))

                    await db.flush()

                # 提取完成后重新查询关系（含新建的）
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

            # 构建 edges（过滤掉端点为 null 或对应实体已删除的关系）
            edges = []
            for rel in relationships:
                if rel.source_id and rel.target_id and rel.source_id in entities_dict and rel.target_id in entities_dict:
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
    async def get_distinct_types() -> list[str]:
        async with async_db_session() as db:
            return await entity_dao.get_distinct_types(db)

    @staticmethod
    async def get_type_stats() -> list[dict]:
        async with async_db_session() as db:
            return await entity_dao.get_type_stats(db)

    @staticmethod
    async def get_select(name: str | None = None, entity_type: str | list[str] | None = None, file_types: list[str] | None = None, sort_field: str = 'created_time', sort_order: str = 'desc') -> Select:
        from backend.common.context import get_current_user
        current_user = get_current_user()
        create_user = None if (current_user is None or current_user.is_superuser) else current_user.id
        return await entity_dao.get_list(name=name, entity_type=entity_type, file_types=file_types, create_user=create_user, sort_field=sort_field, sort_order=sort_order)

    @staticmethod
    async def get_all() -> Sequence[Entity]:
        async with async_db_session() as db:
            entitys = await entity_dao.get_all(db)
            return entitys

    @staticmethod
    async def create(*, obj: CreateEntityParam) -> None:
        from backend.common.context import get_current_user
        from backend.app.admin.model.sys_entity import Entity
        current_user = get_current_user()
        user_id = current_user.id if current_user else None
        async with async_db_session.begin() as db:
            entity = Entity(
                name=obj.name,
                description=obj.description,
                entity_type=obj.entity_type,
                properties=obj.properties,
                create_user=user_id,
            )
            db.add(entity)

    @staticmethod
    async def update(*, pk: int, obj: UpdateEntityParam) -> int:
        from backend.common.context import get_current_user
        current_user = get_current_user()
        async with async_db_session.begin() as db:
            if current_user and not current_user.is_superuser:
                entity = await entity_dao.get(db, pk)
                if not entity or entity.create_user != current_user.id:
                    raise errors.ForbiddenError(msg='无权限修改此实体')
            count = await entity_dao.update(db, pk, obj)
            return count

    @staticmethod
    async def delete(*, pk: list[int]) -> int:
        from backend.common.context import get_current_user
        current_user = get_current_user()
        async with async_db_session.begin() as db:
            if current_user and not current_user.is_superuser:
                count = await entity_dao.delete_owned(db, pk, owner_id=current_user.id)
            else:
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
    async def _get_valid_entity_types(db) -> list[str]:
        """获取所有有效的实体类型（预设 + 用户自定义，去重）"""
        from sqlalchemy import select
        from backend.app.admin.model.sys_entity_type import EntityType

        predefined = list(EntityService.DEFAULT_EDITABLE_FIELDS.keys())

        result = await db.execute(select(EntityType.name))
        custom_types = [row[0] for row in result.all()]

        seen = set(predefined)
        all_types = list(predefined)
        for t in custom_types:
            if t not in seen:
                all_types.append(t)
                seen.add(t)

        return all_types

    @staticmethod
    async def _search_docs_by_name(db, entity_name: str) -> list[dict]:
        """
        通过实体名称全文检索相关文档分块

        :return: [{'doc_id': int, 'doc_title': str, 'chunks': list[str]}]
        """
        from backend.app.admin.crud.crud_doc_chunk import sys_doc_chunk_dao
        cut = jieba.cut_for_search(entity_name)
        keyword = ' '.join(list(cut))
        return await sys_doc_chunk_dao.search_doc_ids_by_keyword(db, keyword, limit=20)

    @staticmethod
    async def _get_related_doc_contents(db, entity) -> tuple[list[dict], list[int]]:
        """
        获取实体相关文档内容（全文检索命中的 chunk_text）

        :param db: 数据库会话
        :param entity: 实体对象
        :return: (search_results 原始列表, 尚未建立关联的doc_id列表)
                 search_results 每项格式: {'doc_id': int, 'doc_title': str, 'chunks': list[str]}
        """
        # 已关联的 doc_id 集合（仅用于判断是否需要新建关联）
        existing_doc_ids = {doc.id for doc in entity.docs} if entity.docs else set()

        # 全文检索包含实体名称的文档，返回原始结构供上层做 token 预算选择
        search_results = await EntityService._search_docs_by_name(db, entity.name)

        # 保存检索结果到实体的 matched_chunks 字段
        entity.matched_chunks = search_results

        # 识别尚未关联的文档
        new_doc_ids = [
            doc_info['doc_id']
            for doc_info in search_results
            if doc_info['doc_id'] not in existing_doc_ids
        ]

        return search_results, new_doc_ids

    @staticmethod
    async def _ai_extract_relationships(entity_name: str, entity_type: str | None, search_results: list[dict]) -> list[dict]:
        """
        调用 AI 从文档内容中提取该实体与其他实体的关系

        :return: [{'target_name': str, 'target_type': str, 'relation_type': str, 'description': str, 'weight': int}]
        """
        system_prompt = f'''你是一个信息提取专家。根据提供的实体信息和相关文档内容，提取该实体与其他实体的关系。

请严格按照以下JSON数组格式输出，只输出JSON，不要有其他内容：
[
  {{
    "target_name": "相关实体名称",
    "target_type": "相关实体类型（人物/组织/事件/地点等）",
    "relation_type": "关系类型（简洁词语，如：上级、合作、参与、管理等）",
    "description": "关系的详细说明",
    "weight": 5
  }}
]

注意：
1. 只输出JSON数组，不要有任何其他文字说明
2. weight为1-10的整数，表示关系强度
3. 只提取有明确文档依据的关系，不要推测
4. target_name必须是具体实体名称，不能是泛指名词（如"企业""组织"等）
5. 如果没有找到任何关系，返回空数组 []'''

        context_parts = [
            f'实体名称: {entity_name}',
            f'实体类型: {entity_type or "未知"}',
        ]

        CHARS_PER_TOKEN = 2
        MAX_INPUT_TOKENS = 24000
        base_tokens = (len(system_prompt) + len('\n'.join(context_parts))) // CHARS_PER_TOKEN
        budget = MAX_INPUT_TOKENS - base_tokens

        selected_lines: list[str] = []
        used = 0
        for doc_info in search_results:
            doc_header = f'[{doc_info["doc_title"]}]:'
            for i, chunk in enumerate(doc_info['chunks']):
                line = f'{doc_header} {chunk}' if i == 0 else chunk
                line_tokens = len(line) // CHARS_PER_TOKEN
                if used + line_tokens > budget:
                    continue
                selected_lines.append(line)
                used += line_tokens

        if not selected_lines:
            return []

        context_parts.append('关联文档内容:\n' + '\n'.join(selected_lines))
        user_input = '\n'.join(context_parts)

        try:
            import time
            _t0 = time.time()
            log.debug(f'_ai_extract_relationships [{entity_name}] 调用 AI，输入上下文长度: {len(user_input)} chars, 约 {len(user_input) // CHARS_PER_TOKEN} tokens')
            ai_response = await llm_service.get_llm_response(system_prompt, user_input)
            _elapsed = time.time() - _t0
            log.debug(f'_ai_extract_relationships [{entity_name}] AI 响应耗时: {_elapsed:.3f}s, 原始输出: {ai_response}')
            response_text = ai_response.strip()
            if response_text.startswith('```'):
                lines = response_text.split('\n')
                inner: list[str] = []
                in_block = False
                for line in lines:
                    if line.startswith('```') and not in_block:
                        in_block = True
                        continue
                    elif line.startswith('```') and in_block:
                        break
                    elif in_block:
                        inner.append(line)
                response_text = '\n'.join(inner)
            result = json.loads(response_text)
            return result if isinstance(result, list) else []
        except Exception as e:
            log.error(f'_ai_extract_relationships [{entity_name}] 失败: {repr(e)}')
            return []

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
            json_template_fields.append('    "画像": "实体详细画像（Markdown格式输出，涵盖背景、经历、特征等关键信息）"')
            json_template = '{\n' + ',\n'.join(json_template_fields) + '\n}'

            # 构建 system prompt（需提前构建，以便计算 token 预算）
            system_prompt = f'''你是一个信息提取专家。根据提供的实体信息和相关文档内容，提取{entity.entity_type}的属性信息。

请严格按照以下JSON格式输出，只输出JSON，不要有其他内容：
{json_template}

注意：
1. 如果某个属性无法从提供的信息中推断出来，请填写"未知"
2. 只输出JSON格式，不要有任何其他文字说明
3. 确保输出是有效的JSON格式
4. "描述" 字段必须填写，用于简要描述此{entity.entity_type}的关键信息
5. "画像" 字段必须填写，使用Markdown格式撰写详细的实体画像，内容尽可能全面丰富
6. JSON的key必须使用中文，严格按照上述模板中的字段名'''

            # 构建上下文信息
            context_parts = []
            context_parts.append(f'实体名称: {entity.name}')
            context_parts.append(f'实体类型: {entity.entity_type}')
            if entity.description:
                context_parts.append(f'现有描述: {entity.description}')

            # 获取关联文档内容（直接关联 + 全文检索）
            search_results, new_doc_ids = await EntityService._get_related_doc_contents(db, entity)

            if search_results:
                # Token 感知的贪心 chunk 填充：
                # 以完整 chunk 为单位逐个尝试加入，跳过放不下的 chunk，
                # 确保每个被选中的 chunk 是完整的语义单元。
                #
                # 保守估算：中英混合文本约 2 字符 ≈ 1 token
                CHARS_PER_TOKEN = 2
                # 总输入预算（留出 ~8000 token 给 system prompt 和模型输出）
                MAX_INPUT_TOKENS = 24000

                base_tokens = (len(system_prompt) + len('\n'.join(context_parts))) // CHARS_PER_TOKEN
                budget = MAX_INPUT_TOKENS - base_tokens

                selected_lines: list[str] = []
                used = 0

                for doc_info in search_results:
                    doc_header = f'[{doc_info["doc_title"]}]:'
                    for i, chunk in enumerate(doc_info['chunks']):
                        # 首个 chunk 带文档标题前缀
                        line = f'{doc_header} {chunk}' if i == 0 else chunk
                        line_tokens = len(line) // CHARS_PER_TOKEN
                        if used + line_tokens > budget:
                            # 放不下就跳过这个 chunk，继续尝试后续更短的 chunk
                            continue
                        selected_lines.append(line)
                        used += line_tokens

                if selected_lines:
                    context_parts.append('关联文档内容:\n' + '\n'.join(selected_lines))

            user_input = '\n'.join(context_parts)

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

                # 提取 "画像" 字段
                profile = result.pop('画像', None)

                # 剩余的作为 properties
                properties = result

                # 更新实体的 properties、description 和 profile 字段
                await entity_dao.update_properties(db, pk, properties, description, profile)

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

                # 返回结果包含 properties、description 和 profile
                return {'properties': properties, 'description': description, 'profile': profile}

            except json.JSONDecodeError as e:
                log.error(f'AI 响应解析失败: {ai_response}, 错误: {e}')
                raise errors.RequestError(msg='AI 响应格式错误，无法解析为JSON')
            except Exception as e:
                log.error(f'生成属性失败: {e}')
                raise errors.RequestError(msg=f'生成属性失败: {str(e)}')



    @staticmethod
    async def extract_timeline_by_ai(*, pk: int) -> list[dict]:
        """
        调用 AI 从文档内容中提取该实体的时间轴脉络

        :param pk: 实体ID
        :return: [{'time': '2010年9月', 'event': '进入北京大学就读'}]
        """
        from sqlalchemy import select

        async with async_db_session.begin() as db:
            entity = await entity_dao.get(db, pk)
            if not entity:
                raise errors.NotFoundError(msg='实体不存在')

            system_prompt = f'''你是一个信息提取专家。根据提供的实体信息和相关文档内容，提取"{entity.name}"的时间轴脉络。

请提取该实体人生/发展历程中的重要时间节点和对应事件，如入学、毕业、参加工作、晋升、获奖、结婚、出版著作等。

请严格按照以下JSON数组格式输出，只输出JSON，不要有其他内容：
[
  {{
    "time": "时间（如：2010年9月）",
    "event": "事件描述（简洁清晰的一句话）"
  }}
]

注意：
1. 只输出JSON数组，不要有任何其他文字说明
2. 每个事件包含 time 和 event 两个字段
3. 按照时间先后顺序排列（从早到晚）
4. time 只写时间本身，不要加"时间："前缀
5. event 是事件本身的描述，不要加"事件："或"发生："前缀
6. 只提取有明确文档依据的事件，不要推测编造
7. 如果没有找到任何时间轴事件，返回空数组 []'''

            context_parts = []
            context_parts.append(f'实体名称: {entity.name}')
            context_parts.append(f'实体类型: {entity.entity_type or "未知"}')
            if entity.description:
                context_parts.append(f'现有描述: {entity.description}')

            # 获取关联文档内容
            search_results, new_doc_ids = await EntityService._get_related_doc_contents(db, entity)

            if search_results:
                CHARS_PER_TOKEN = 2
                MAX_INPUT_TOKENS = 24000

                base_tokens = (len(system_prompt) + len('\n'.join(context_parts))) // CHARS_PER_TOKEN
                budget = MAX_INPUT_TOKENS - base_tokens

                selected_lines: list[str] = []
                used = 0

                for doc_info in search_results:
                    doc_header = f'[{doc_info["doc_title"]}]:'
                    for i, chunk in enumerate(doc_info['chunks']):
                        line = f'{doc_header} {chunk}' if i == 0 else chunk
                        line_tokens = len(line) // CHARS_PER_TOKEN
                        if used + line_tokens > budget:
                            continue
                        selected_lines.append(line)
                        used += line_tokens

                if selected_lines:
                    context_parts.append('关联文档内容:\n' + '\n'.join(selected_lines))

            user_input = '\n'.join(context_parts)

            try:
                ai_response = await llm_service.get_llm_response(system_prompt, user_input)
                log.info(f'extract_timeline_by_ai AI 响应: {ai_response}')

                response_text = ai_response.strip()
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
                timeline = result if isinstance(result, list) else []

                # 保存到实体
                await entity_dao.update_timeline(db, pk, timeline)

                # 为新发现的文档创建关联
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

                return timeline

            except json.JSONDecodeError as e:
                log.error(f'extract_timeline_by_ai JSON 解析失败: {ai_response}, 错误: {e}')
                raise errors.RequestError(msg='AI 响应格式错误，无法解析为JSON')
            except Exception as e:
                log.error(f'extract_timeline_by_ai 失败: {repr(e)}')
                raise errors.RequestError(msg=f'提取时间轴失败: {str(e)}')

    @staticmethod
    async def find_abstract_entities(
        *,
        entity_type: str | list[str] | None = None,
        batch_size: int = 50,
    ) -> list[dict]:
        """
        筛选出名称为泛指抽象名词（没有具体指代对象）的实体。
        例如：「企业」「研究」「技术」「项目」「工作」等。
        仅做筛选，不删除。

        :param entity_type: 限定实体类型范围，None 表示全部类型
        :param batch_size: 每批发送给 AI 的实体数量
        :return: 抽象实体列表，每项格式为 {'id': int, 'name': str, 'entity_type': str}
        """
        from sqlalchemy import select

        async with async_db_session() as db:
            stmt = select(Entity.id, Entity.name, Entity.entity_type)
            if entity_type:
                if isinstance(entity_type, str):
                    stmt = stmt.where(Entity.entity_type == entity_type)
                else:
                    stmt = stmt.where(Entity.entity_type.in_(entity_type))
            result = await db.execute(stmt)
            all_entities = [
                {'id': row.id, 'name': row.name, 'entity_type': row.entity_type}
                for row in result.all()
                if row.name
            ]

        if not all_entities:
            return []

        system_prompt = (
            '你是一个语言学专家。你的任务是从实体名称列表中找出那些「泛指抽象名词」——'
            '即没有具体指代对象的通用词语，例如：企业、研究、技术、项目、工作、'
            '问题、情况、方面、领域、活动、事项、系统、机制、模式、力量、资源、能力、服务、产品、方案。\n'
            '相反，具体实体（如：阿里巴巴、张伟、新冠疫情、北京大学）不属于此类。\n\n'
            '输入：JSON 数组，每项包含 id 和 name 字段。\n'
            '输出：仅返回属于泛指抽象名词的那些项的 id 列表，格式为 JSON 数组（只有数字），'
            '不要有任何其他文字。\n'
            '示例输出：[12, 37, 105]'
        )

        abstract_ids: set[int] = set()

        for i in range(0, len(all_entities), batch_size):
            batch = all_entities[i: i + batch_size]
            user_input = json.dumps(
                [{'id': e['id'], 'name': e['name']} for e in batch],
                ensure_ascii=False,
            )
            try:
                ai_response = await llm_service.get_llm_response(system_prompt, user_input)
                response_text = ai_response.strip()
                # 去掉可能存在的 markdown 代码块包装
                if response_text.startswith('```'):
                    lines = response_text.split('\n')
                    inner = []
                    in_block = False
                    for line in lines:
                        if line.startswith('```') and not in_block:
                            in_block = True
                            continue
                        elif line.startswith('```') and in_block:
                            break
                        elif in_block:
                            inner.append(line)
                    response_text = '\n'.join(inner)
                ids = json.loads(response_text)
                if isinstance(ids, list):
                    abstract_ids.update(int(x) for x in ids if isinstance(x, (int, float)))
            except Exception as e:
                log.error(f'find_abstract_entities 批次 {i // batch_size + 1} 处理失败: {repr(e)}')

        return [e for e in all_entities if e['id'] in abstract_ids]

    @staticmethod
    async def parse_file(*, content: bytes, filename: str) -> dict:
        """
        解析 CSV/Excel 文件内容，返回表头和数据预览

        :param content: 文件二进制内容
        :param filename: 文件名（用于推断后缀）
        :return: { headers, preview_rows, total_rows }
        """
        suffix = os.path.splitext(filename)[1].lower()

        try:
            if suffix in ('.csv',):
                import chardet
                encoding = chardet.detect(content)['encoding'] or 'utf-8'
                df = pd.read_csv(io.BytesIO(content), encoding=encoding)
            elif suffix in ('.xlsx',):
                df = pd.read_excel(io.BytesIO(content), engine='openpyxl')
            elif suffix in ('.xls',):
                df = pd.read_excel(io.BytesIO(content), engine='xlrd')
            else:
                raise ValueError(f'不支持的文件格式: {suffix}')
        except Exception as e:
            log.error(f'解析文件失败: {repr(e)}')
            raise errors.RequestError(msg=f'文件解析失败: {str(e)}')

        if df.empty:
            raise errors.RequestError(msg='文件为空')

        # 列名去空、去重
        df.columns = [str(c).strip() if pd.notna(c) else f'column_{i}' for i, c in enumerate(df.columns)]
        headers = list(df.columns)

        # 替换 NaN 为 None
        df = df.where(pd.notna(df), None)

        preview_rows = df.head(10).to_dict(orient='records')
        total_rows = len(df)

        # 全量数据转为二维数组（用于 batch-import）
        all_rows = df.values.tolist()

        return {
            'headers': headers,
            'preview_rows': preview_rows,
            'total_rows': total_rows,
            'rows': all_rows,
        }

    @staticmethod
    async def batch_import(*, obj: BatchImportParam) -> dict:
        """
        批量导入实体

        :param obj: 批量导入参数
        :return: { total, created, errors }
        """
        from backend.common.context import get_current_user
        from backend.app.admin.crud.crud_entity_type import entity_type_dao
        from backend.app.admin.model.sys_entity_type import EntityType

        current_user = get_current_user()
        user_id = current_user.id if current_user else None

        async with async_db_session.begin() as db:
            created_count = 0
            errors: list[dict] = []

            # 1. 可选：创建实体类型
            entity_type_id = None
            if obj.create_entity_type and obj.entity_type_name:
                existing = await entity_type_dao.get_by_name(db, obj.entity_type_name)
                if existing:
                    entity_type_id = existing.id
                else:
                    # 收集映射到 properties 的字段名
                    field_def = [
                        mapping.field_name
                        for mapping in obj.field_mapping.values()
                        if mapping.target == 'properties' and mapping.field_name
                    ]
                    et = EntityType(
                        name=obj.entity_type_name,
                        description=obj.entity_type_description,
                        field_definition=field_def if field_def else None,
                    )
                    db.add(et)
                    await db.flush()
                    entity_type_id = et.id

            # 2. 批量创建实体
            for row_idx, row in enumerate(obj.rows):
                try:
                    entity_data: dict = {}
                    properties: dict = {}
                    type_from_row: str | None = None

                    for col_idx, header in enumerate(obj.file_headers):
                        if col_idx >= len(row):
                            continue
                        value = row[col_idx]
                        if value is None or value == '':
                            continue

                        mapping = obj.field_mapping.get(header)
                        if not mapping:
                            continue

                        if mapping.target == 'name':
                            entity_data['name'] = str(value)
                        elif mapping.target == 'description':
                            entity_data['description'] = str(value)
                        elif mapping.target == 'entity_type':
                            type_from_row = str(value)
                        elif mapping.target == 'properties' and mapping.field_name:
                            properties[mapping.field_name] = value

                    if not entity_data.get('name'):
                        errors.append({'row': row_idx + 1, 'error': '缺少名称字段'})
                        continue

                    # 实体类型优先级: 行级 entity_type > 全局 entity_type_name
                    final_type = type_from_row or obj.entity_type_name

                    entity = Entity(
                        name=entity_data['name'],
                        description=entity_data.get('description'),
                        entity_type=final_type,
                        properties=properties if properties else None,
                        entity_type_id=entity_type_id,
                        create_user=user_id,
                    )
                    db.add(entity)
                    created_count += 1

                except Exception as e:
                    log.error(f'批量导入第 {row_idx + 1} 行失败: {repr(e)}')
                    errors.append({'row': row_idx + 1, 'error': str(e)})

            await db.flush()

        return {
            'total': len(obj.rows),
            'created': created_count,
            'errors': errors,
        }


entity_service = EntityService()