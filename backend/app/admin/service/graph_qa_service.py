#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图谱问答服务

流程：
  1. LLM 从问题中提取命名实体
  2. 模糊查询 sys_entity 找到种子实体
  3. 查 sys_entity_relationship 取 1 跳关系子图
  4. 序列化子图为文本 context
  5. LLM 基于 context 生成答案
  6. 返回 answer + entities + relations
"""
import json
import re

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin.model.sys_entity import Entity
from backend.app.admin.crud.crud_entity_relationship import entity_relation_dao
from backend.app.admin.schema.unified_search_schema import SourceItem
from backend.app.admin.service.ai_service import call_llm
from backend.common.log import log

_MAX_SEED_ENTITIES = 5
_MAX_RELATIONS = 30
_PROFILE_PREVIEW = 400


async def _extract_entity_names(question: str) -> list[str]:
    system = (
        '从用户问题中提取所有命名实体（人名、地名、机构名、项目名、产品名等）。'
        '只返回 JSON 数组，例如 ["张三", "腾讯", "北京"]。若无实体则返回 []。'
        '不要输出任何其他内容。'
    )
    try:
        raw = await call_llm(question, system, {'llm': {'temperature': 0, 'max_tokens': 100}})
        m = re.search(r'\[.*?\]', raw.strip(), re.DOTALL)
        if m:
            names = json.loads(m.group())
            return [n.strip() for n in names if isinstance(n, str) and n.strip()]
    except Exception as e:
        log.warning(f'[graph_qa] 实体名提取失败: {repr(e)}')
    return []


async def _find_entities_by_names(db: AsyncSession, names: list[str]) -> list[Entity]:
    conditions = [Entity.name.ilike(f'%{n}%') for n in names]
    stmt = (
        select(Entity)
        .where(or_(*conditions))
        .limit(_MAX_SEED_ENTITIES * 3)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()
    seen: set[int] = set()
    deduped: list[Entity] = []
    for e in rows:
        if e.id not in seen:
            seen.add(e.id)
            deduped.append(e)
    return deduped[:_MAX_SEED_ENTITIES]


async def _get_entities_by_ids(db: AsyncSession, ids: list[int]) -> list[Entity]:
    if not ids:
        return []
    stmt = select(Entity).where(Entity.id.in_(ids))
    result = await db.execute(stmt)
    return list(result.scalars().all())


def _build_context(
    seed_entities: list[Entity],
    entity_map: dict[int, Entity],
    relations: list,
) -> str:
    parts: list[str] = ['## 相关实体']
    for e in seed_entities:
        line = f'- **{e.name}**（{e.entity_type or "未知类型"}）'
        detail = e.profile or e.description
        if detail:
            line += f'：{detail[:_PROFILE_PREVIEW]}'
        parts.append(line)

    if relations:
        parts.append('\n## 关联关系')
        for r in relations:
            src = entity_map.get(r.source_id)
            tgt = entity_map.get(r.target_id)
            src_name = src.name if src else f'#{r.source_id}'
            tgt_name = tgt.name if tgt else f'#{r.target_id}'
            line = f'- {src_name} —[{r.relation_type or "关联"}]→ {tgt_name}'
            if r.description:
                line += f'（{r.description[:120]}）'
            parts.append(line)

    return '\n'.join(parts)


async def query_graph(question: str, db: AsyncSession) -> SourceItem:
    # 1. Extract entity names
    entity_names = await _extract_entity_names(question)
    log.info(f'[graph_qa] 提取实体={entity_names!r}')

    if not entity_names:
        return SourceItem(
            type='graph',
            path_answer='问题中未识别到具体实体名称，无法进行图谱查询。',
            entities=[],
            relations=[],
        )

    # 2. Find seed entities
    seed_entities = await _find_entities_by_names(db, entity_names)
    if not seed_entities:
        return SourceItem(
            type='graph',
            path_answer=f'知识图谱中未找到与 "{", ".join(entity_names)}" 相关的实体。',
            entities=[],
            relations=[],
        )

    # 3. Fetch 1-hop relations, sort by weight desc
    seed_ids = [e.id for e in seed_entities]
    all_relations = await entity_relation_dao.get_by_entity_ids(db, seed_ids)
    relations = sorted(all_relations, key=lambda r: r.weight or 0, reverse=True)[:_MAX_RELATIONS]

    # 4. Collect all involved entity ids and fetch neighbor entities
    all_ids: set[int] = set(seed_ids)
    for r in relations:
        if r.source_id:
            all_ids.add(r.source_id)
        if r.target_id:
            all_ids.add(r.target_id)
    neighbor_entities = await _get_entities_by_ids(db, list(all_ids - set(seed_ids)))
    entity_map: dict[int, Entity] = {e.id: e for e in seed_entities + neighbor_entities}

    # 5. Build context and generate LLM answer
    context = _build_context(seed_entities, entity_map, relations)
    system_prompt = (
        '你是一个知识图谱问答助手。根据以下图谱信息回答用户问题，用简洁清晰的中文作答。'
        '如果图谱信息不足以回答，请如实说明。\n\n'
        f'{context}'
    )
    try:
        answer = await call_llm(
            question,
            system_prompt,
            {'llm': {'temperature': 0.3, 'max_tokens': 600}},
        )
        answer = answer.strip()
    except Exception as e:
        log.error(f'[graph_qa] LLM 答案生成失败: {repr(e)}')
        answer = context

    # 6. Serialize for response
    entities_out = [
        {
            'id': e.id,
            'name': e.name,
            'entity_type': e.entity_type,
            'description': (e.description or '')[:200],
        }
        for e in entity_map.values()
    ]
    relations_out = [
        {
            'source_id': r.source_id,
            'source_name': entity_map[r.source_id].name if r.source_id in entity_map else None,
            'target_id': r.target_id,
            'target_name': entity_map[r.target_id].name if r.target_id in entity_map else None,
            'relation_type': r.relation_type,
            'description': r.description,
            'weight': r.weight,
        }
        for r in relations
    ]

    return SourceItem(
        type='graph',
        path_answer=answer,
        entities=entities_out,
        relations=relations_out,
    )
