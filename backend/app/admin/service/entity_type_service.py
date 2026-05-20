#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import io
import json
import re
from datetime import datetime
from typing import List

import duckdb
import pandas as pd
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin.crud.crud_entity_type import entity_type_dao
from backend.app.admin.crud.crud_entity_relationship import entity_relation_dao
from backend.app.admin.model import EntityType
from backend.app.admin.model.sys_entity import Entity
from backend.app.admin.model.sys_entity_relationship import EntityRelation
from backend.app.admin.schema.entity_type import CreateEntityTypeParam, UpdateEntityTypeParam
from backend.app.admin.service.llm_service import llm_service
from backend.common.exception import errors
from backend.core.conf import settings
from backend.database.db_pg import async_db_session
from backend.utils.oss_client import minio_client, put_object


class EntityTypeService:
    """实体类型服务"""

    @staticmethod
    async def get(*, pk: int) -> EntityType:
        """获取实体类型详情"""
        async with async_db_session() as db:
            entity_type = await entity_type_dao.get(db, pk)
            if not entity_type:
                raise errors.NotFoundError(msg='实体类型不存在')
            return entity_type

    @staticmethod
    async def get_select(*, name: str | None = None):
        """获取实体类型列表（用于分页查询）"""
        return await entity_type_dao.get_list(name=name)

    @staticmethod
    async def get_by_name(*, name: str) -> EntityType | None:
        """根据名称获取实体类型"""
        async with async_db_session() as db:
            return await entity_type_dao.get_by_name(db, name)

    @staticmethod
    async def create(*, obj: CreateEntityTypeParam) -> None:
        """创建实体类型"""
        async with async_db_session.begin() as db:
            # 检查名称是否已存在
            existing = await entity_type_dao.get_by_name(db, obj.name)
            if existing:
                raise errors.ForbiddenError(msg='实体类型名称已存在')
            await entity_type_dao.create(db, obj)

    @staticmethod
    async def update(*, pk: int, obj: UpdateEntityTypeParam) -> int:
        """更新实体类型"""
        async with async_db_session.begin() as db:
            # 检查实体类型是否存在
            entity_type = await entity_type_dao.get(db, pk)
            if not entity_type:
                raise errors.NotFoundError(msg='实体类型不存在')

            # 如果更新了名称，检查新名称是否已被其他实体类型使用
            if obj.name and obj.name != entity_type.name:
                existing = await entity_type_dao.get_by_name(db, obj.name)
                if existing:
                    raise errors.ForbiddenError(msg='实体类型名称已存在')

            return await entity_type_dao.update(db, pk, obj)

    @staticmethod
    async def delete(*, pk: List[int]) -> int:
        """删除实体类型"""
        async with async_db_session.begin() as db:
            return await entity_type_dao.delete(db, pk)

    @staticmethod
    def _entity_to_row(entity: Entity) -> dict:
        """将实体转为扁平 dict，非基础类型的 property 值序列化为 JSON 字符串"""
        row: dict = {
            'id': entity.id,
            'name': entity.name,
            'description': entity.description,
            'entity_type': entity.entity_type,
        }
        if entity.properties:
            for key, value in entity.properties.items():
                if isinstance(value, (list, dict)):
                    row[key] = json.dumps(value, ensure_ascii=False)
                else:
                    row[key] = value
        return row

    @staticmethod
    async def export_entities(*, pk: int, format: str) -> tuple[bytes, str, str]:
        """导出指定实体类型下的所有实体"""
        async with async_db_session() as db:
            entity_type = await entity_type_dao.get(db, pk)
            if not entity_type:
                raise errors.NotFoundError(msg='实体类型不存在')

            stmt = select(Entity).where(
                or_(Entity.entity_type_id == pk, Entity.entity_type == entity_type.name)
            )
            result = await db.execute(stmt)
            entities = result.scalars().all()

        rows = [EntityTypeService._entity_to_row(e) for e in entities]

        df = pd.DataFrame(rows)

        buf = io.BytesIO()
        if format == 'csv':
            df.to_csv(buf, index=False, encoding='utf-8-sig')
            filename = f'{entity_type.name}_entities.csv'
            media_type = 'text/csv'
        elif format == 'parquet':
            df.to_parquet(buf, index=False)
            filename = f'{entity_type.name}_entities.parquet'
            media_type = 'application/octet-stream'
        else:
            raise errors.RequestError(msg=f'不支持的导出格式: {format}')

        buf.seek(0)
        return buf.getvalue(), filename, media_type

    @staticmethod
    async def lake_entities(*, pk: int) -> str:
        """将指定实体类型下的所有实体导出为 Parquet 并入湖（存入 MinIO）"""
        async with async_db_session() as db:
            entity_type = await entity_type_dao.get(db, pk)
            if not entity_type:
                raise errors.NotFoundError(msg='实体类型不存在')

            stmt = select(Entity).where(
                or_(Entity.entity_type_id == pk, Entity.entity_type == entity_type.name)
            )
            result = await db.execute(stmt)
            entities = result.scalars().all()

        rows = [EntityTypeService._entity_to_row(e) for e in entities]

        df = pd.DataFrame(rows)

        buf = io.BytesIO()
        df.to_parquet(buf, index=False)
        buf.seek(0)
        data = buf.getvalue()

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name = entity_type.name.replace('/', '_').replace('\\', '_')
        object_name = f'analytics/export/{safe_name}/{safe_name}_{timestamp}.parquet'

        bucket = settings.BUCKET_NAME
        if not bucket:
            raise errors.RequestError(msg='MinIO BUCKET_NAME 未配置')

        await put_object(bucket, object_name, data, 'application/parquet')
        return object_name


    @staticmethod
    async def extract_relations(*, pk: int, requirement: str) -> dict:
        """根据用户需求，通过 AI + DuckDB 分析 Parquet 数据提取实体关系"""
        async with async_db_session() as db:
            entity_type = await entity_type_dao.get(db, pk)
            if not entity_type:
                raise errors.NotFoundError(msg='实体类型不存在')

        bucket = settings.BUCKET_NAME
        if not bucket:
            raise errors.RequestError(msg='MinIO BUCKET_NAME 未配置')

        safe_name = entity_type.name.replace('/', '_').replace('\\', '_')
        prefix = f'analytics/export/{safe_name}/'

        objects = list(minio_client.list_objects(bucket, prefix=prefix))
        if not objects:
            await EntityTypeService.lake_entities(pk=pk)
            objects = list(minio_client.list_objects(bucket, prefix=prefix))
            if not objects:
                raise errors.RequestError(msg='入湖失败，请重试')

        latest = max(objects, key=lambda o: o.last_modified)
        response = minio_client.get_object(bucket, latest.object_name)
        parquet_data = response.read()

        df = pd.read_parquet(io.BytesIO(parquet_data))
        if df.empty:
            return {'sql': '', 'count': 0, 'relationships': []}

        schema_info = {
            '列数': len(df.columns),
            '列名': list(df.columns),
            '数据类型': {col: str(dtype) for col, dtype in df.dtypes.items()},
            '前5行数据': df.head().to_dict('records'),
        }

        sample_data = pd.DataFrame(schema_info['前5行数据']).to_string()
        col_names = ', '.join(schema_info['列名'])
        row_count = len(df)

        system_context = (
            '你是一个数据分析专家。有一个包含"{name}"类型实体的 Parquet 文件，结构如下：\n\n'
            '列名: {cols}\n'
            '行数: {rows}\n\n'
            '前5行示例数据：\n{data}\n\n'
            '用户需求：{req}\n\n'
            '请生成 DuckDB 兼容的 SQL 查询语句，从该数据中发现实体间的关系。\n'
            '要求：\n'
            '1. 表名固定为 data_table\n'
            '2. 只返回 SQL 语句，用 ```sql ... ``` 包裹，不要额外解释\n'
            '3. SQL 必须是 SELECT 查询，返回列如下：\n'
            '   - source_id  : 实体 id（整数）\n'
            '   - source_name : 实体名称（字符串）\n'
            '   - target_id  : 相关实体 id（整数）\n'
            '   - target_name : 相关实体名称（字符串）\n'
            '   - relation_type : 关系类型名称（字符串）\n'
            '   - weight     : 关系权重（整数，默认 1）\n'
            '   - description: 关系描述（字符串）\n'
            '4. 使用自连接（self-join）来匹配不同实体的相同属性值\n'
            '5. 用 a.id < b.id 避免重复对\n'
            '6. 排除 source_id = target_id 的自指情况\n'
            '7. 如果某列为空字符串或 NULL，不应作为关系依据\n'
            '8. 若无法提取任何关系，返回 SELECT 0 AS source_id, \'\' AS source_name, 0 AS target_id, \'\' AS target_name, \'\' AS relation_type, 0 AS weight, \'\' AS description LIMIT 0\n\n'
            '示例 SQL：\n'
            '```sql\n'
            "SELECT a.id AS source_id, a.name AS source_name, b.id AS target_id, b.name AS target_name, '同事' AS relation_type, 1 AS weight, CONCAT('同在', a.organization, '工作') AS description FROM data_table a, data_table b WHERE a.id < b.id AND a.organization IS NOT NULL AND a.organization <> '' AND a.organization = b.organization\n"
            '```'
        ).format(name=entity_type.name, cols=col_names, rows=row_count, data=sample_data, req=requirement)

        sql_query = await llm_service.get_llm_response(system_context, f'需求：{requirement}')

        sql_query = sql_query.strip()
        m = re.search(r'```sql\s*(.*?)\s*```', sql_query, re.DOTALL)
        if m:
            sql_query = m.group(1).strip()
        sql_query = sql_query.rstrip(';').strip()

        conn = duckdb.connect(':memory:')
        try:
            conn.register('data_table', df)
            result = conn.execute(sql_query).fetchdf()
        except Exception as e:
            raise errors.RequestError(msg=f'SQL 执行失败: {e}')
        finally:
            conn.close()

        if result.empty:
            return {'sql': sql_query, 'count': 0, 'relationships': []}

        seen = set()
        rows_to_insert = []
        relationships = []
        for _, row in result.iterrows():
            source_id = int(row['source_id'])
            target_id = int(row['target_id'])
            if source_id == target_id:
                continue
            key = (source_id, target_id, str(row.get('relation_type', '')))
            if key in seen:
                continue
            seen.add(key)
            rel = {
                'source_id': source_id,
                'source_name': str(row.get('source_name', '')),
                'target_id': target_id,
                'target_name': str(row.get('target_name', '')),
                'relation_type': str(row.get('relation_type', '')),
                'weight': int(row.get('weight', 1)),
                'description': str(row.get('description', '')),
            }
            relationships.append(rel)
            rows_to_insert.append({
                'source_id': source_id,
                'target_id': target_id,
                'relation_type': rel['relation_type'],
                'weight': rel['weight'],
                'description': rel['description'],
            })

        if not rows_to_insert:
            return {'sql': sql_query, 'count': 0, 'relationships': []}

        async with async_db_session.begin() as db:
            for r in rows_to_insert:
                db.add(EntityRelation(**r))

        return {
            'sql': sql_query,
            'count': len(relationships),
            'relationships': relationships,
        }


    @staticmethod
    async def analyze_entity_nl(*, question: str) -> dict:
        """通过自然语言分析实体数据"""
        # Step 1: 获取所有有效的实体类型名称
        async with async_db_session() as db:
            predefined = ['人物', '组织', '事件']
            result = await db.execute(select(EntityType.name))
            custom_types = [row[0] for row in result.all()]
            result2 = await db.execute(
                select(Entity.entity_type)
                .where(Entity.entity_type.is_not(None))
                .distinct()
            )
            entity_types_in_use = [row[0] for row in result2.all()]

        seen = set(predefined)
        all_types = list(predefined)
        for t in custom_types:
            if t not in seen:
                all_types.append(t)
                seen.add(t)
        for t in entity_types_in_use:
            if t not in seen:
                all_types.append(t)
                seen.add(t)

        if not all_types:
            raise errors.RequestError(msg='暂无实体类型数据')

        # Step 2: AI 判断应该查询哪个实体类型
        type_prompt = (
            f'用户问题：{question}\n\n'
            f'可用的实体类型：{", ".join(all_types)}\n\n'
            '请分析用户问题，判断应该查询哪个实体类型来回答该问题。只返回实体类型名称，不要任何额外文字。'
        )
        selected_type = await llm_service.get_llm_response(
            '你是一个实体类型分析专家。根据用户的问题，从给定的实体类型列表中选择最相关的实体类型。只返回实体类型名称。',
            type_prompt
        )
        selected_type = selected_type.strip().strip('"').strip("'").strip()

        if selected_type not in seen:
            for tn in all_types:
                if tn in selected_type or selected_type in tn:
                    selected_type = tn
                    break
            else:
                raise errors.RequestError(msg=f'AI选择的实体类型"{selected_type}"不在可用类型列表中')

        # Step 3: 读取 Parquet 数据（优先从 MinIO 湖存储读取）
        bucket = settings.BUCKET_NAME
        if not bucket:
            raise errors.RequestError(msg='MinIO BUCKET_NAME 未配置')

        safe_name = selected_type.replace('/', '_').replace('\\', '_')
        prefix = f'analytics/export/{safe_name}/'
        objects = list(minio_client.list_objects(bucket, prefix=prefix))

        if objects:
            latest = max(objects, key=lambda o: o.last_modified)
            response = minio_client.get_object(bucket, latest.object_name)
            parquet_data = response.read()
            df = pd.read_parquet(io.BytesIO(parquet_data))
        else:
            async with async_db_session() as db:
                stmt = select(Entity).where(Entity.entity_type == selected_type)
                result = await db.execute(stmt)
                entities = result.scalars().all()
            if not entities:
                return {
                    'entity_type': selected_type,
                    'sql': '',
                    'count': 0,
                    'columns': [],
                    'rows': [],
                    'message': f'实体类型"{selected_type}"下没有数据',
                }
            rows_list = [EntityTypeService._entity_to_row(e) for e in entities]
            df = pd.DataFrame(rows_list)

        if df.empty:
            return {
                'entity_type': selected_type,
                'sql': '',
                'count': 0,
                'columns': [],
                'rows': [],
            }

        # Step 4: AI 生成 DuckDB SQL
        sample_data = df.head().to_string()
        col_names = ', '.join(df.columns)
        row_count = len(df)

        system_context = (
            '你是一个数据分析专家。有一个包含"{name}"实体的 Parquet 文件，结构如下：\n\n'
            '列名: {cols}\n'
            '行数: {rows}\n\n'
            '前5行示例数据：\n{data}\n\n'
            '用户问题：{req}\n\n'
            '请生成 DuckDB 兼容的 SQL 查询语句，从该数据中回答用户的问题。\n'
            '要求：\n'
            '1. 表名固定为 data_table\n'
            '2. 只返回 SQL 语句，用 ```sql ... ``` 包裹，不要额外解释\n'
            '3. SQL 必须是 SELECT 查询\n'
            '4. 注意处理 NULL 和空字符串\n'
            '5. 结果列名使用有意义的别名（中文优先），让用户更容易理解'
        ).format(name=selected_type, cols=col_names, rows=row_count, data=sample_data, req=question)

        sql_query = await llm_service.get_llm_response(system_context, f'问题：{question}')
        sql_query = sql_query.strip()
        m = re.search(r'```sql\s*(.*?)\s*```', sql_query, re.DOTALL)
        if m:
            sql_query = m.group(1).strip()
        sql_query = sql_query.rstrip(';').strip()

        # Step 5: 执行 SQL
        conn = duckdb.connect(':memory:')
        try:
            conn.register('data_table', df)
            result = conn.execute(sql_query).fetchdf()
        except Exception as e:
            raise errors.RequestError(msg=f'SQL 执行失败: {e}')
        finally:
            conn.close()

        if result.empty:
            return {
                'entity_type': selected_type,
                'sql': sql_query,
                'count': 0,
                'columns': [],
                'rows': [],
            }

        return {
            'entity_type': selected_type,
            'sql': sql_query,
            'count': len(result),
            'columns': list(result.columns),
            'rows': result.to_dict('records'),
        }


# 创建服务单例
entity_type_service = EntityTypeService()
