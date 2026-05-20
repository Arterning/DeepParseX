#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Path, Request

from backend.app.admin.crud.crud_text2sql import (
    crud_text2sql_column,
    crud_text2sql_example,
    crud_text2sql_query_log,
    crud_text2sql_table,
)
from backend.app.admin.schema.text2sql_schema import (
    CreateExampleParam,
    ExampleResponse,
    FeedbackParam,
    ImportTablesParam,
    QueryLogResponse,
    QueryParam,
    QueryResponse,
    TableDetailResponse,
    TableResponse,
    TableColumnResponse,
    UpdateColumnParam,
    UpdateTableParam,
)
from backend.app.admin.service.text2sql_service import text2sql_service
from backend.common.pagination import DependsPagination, paging_data
from backend.common.response.response_schema import ResponseModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db_pg import CurrentSession
from backend.utils.serializers import select_columns_serialize

router = APIRouter()


# ── 查询 ─────────────────────────────────────────────────────────────────────

@router.post('/query', summary='自然语言查询', dependencies=[DependsJwtAuth])
async def query(request: Request, obj: QueryParam, db: CurrentSession) -> ResponseModel:
    user_id = request.user.id
    result = await text2sql_service.query(
        db, question=obj.question, user_id=user_id, clarification_answer=obj.clarification_answer
    )
    return response_base.success(data=result.model_dump())


@router.post('/feedback', summary='提交查询反馈', dependencies=[DependsJwtAuth])
async def submit_feedback(obj: FeedbackParam, db: CurrentSession) -> ResponseModel:
    await text2sql_service.submit_feedback(db, log_id=obj.log_id, rating=obj.rating, correct_sql=obj.correct_sql)
    return response_base.success(data='提交成功')


@router.get('/history', summary='查询历史', dependencies=[DependsJwtAuth, DependsPagination])
async def get_history(request: Request, db: CurrentSession) -> ResponseModel:
    user_id = request.user.id
    stmt = crud_text2sql_query_log.get_list(user_id=user_id)
    page_data = await paging_data(db, stmt, QueryLogResponse)
    return response_base.success(data=page_data)


@router.get('/history/all', summary='全量查询历史（管理员）', dependencies=[DependsJwtAuth, DependsPagination])
async def get_all_history(db: CurrentSession) -> ResponseModel:
    stmt = crud_text2sql_query_log.get_list()
    page_data = await paging_data(db, stmt, QueryLogResponse)
    return response_base.success(data=page_data)


# ── 元数据管理 ────────────────────────────────────────────────────────────────

@router.get('/tables/available', summary='获取所有可导入的表', dependencies=[DependsJwtAuth])
async def get_available_tables(db: CurrentSession) -> ResponseModel:
    tables = await text2sql_service.get_available_tables(db)
    return response_base.success(data=tables)


@router.post('/tables/import', summary='批量导入表到白名单', dependencies=[DependsJwtAuth])
async def import_tables(request: Request, obj: ImportTablesParam, db: CurrentSession) -> ResponseModel:
    user_id = request.user.id
    tables = await text2sql_service.import_tables(db, obj.table_names, user_id)
    data = [TableResponse.model_validate(t, from_attributes=True).model_dump() for t in tables]
    return response_base.success(data=data)


@router.get('/tables', summary='获取白名单表列表', dependencies=[DependsJwtAuth, DependsPagination])
async def get_tables(db: CurrentSession) -> ResponseModel:
    stmt = crud_text2sql_table.get_list()
    page_data = await paging_data(db, stmt, TableResponse)
    return response_base.success(data=page_data)


@router.get('/tables/{pk}', summary='获取表详情（含字段）', dependencies=[DependsJwtAuth])
async def get_table(pk: Annotated[int, Path(...)], db: CurrentSession) -> ResponseModel:
    table = await crud_text2sql_table.get_with_columns(db, pk)
    if not table:
        return response_base.fail(message='表不存在')
    result = TableDetailResponse(
        **{k: v for k, v in select_columns_serialize(table).items()},
        has_embedding=table.embedding is not None,
        columns=[
            TableColumnResponse.model_validate(c, from_attributes=True)
            for c in table.columns
        ],
    )
    return response_base.success(data=result.model_dump())


@router.put('/tables/{pk}', summary='更新表元数据', dependencies=[DependsJwtAuth])
async def update_table(
    pk: Annotated[int, Path(...)], obj: UpdateTableParam, db: CurrentSession
) -> ResponseModel:
    await crud_text2sql_table.update(db, pk, obj)
    await db.commit()
    return response_base.success(data='更新成功')


@router.delete('/tables/{pk}', summary='从白名单移除表', dependencies=[DependsJwtAuth])
async def delete_table(pk: Annotated[int, Path(...)], db: CurrentSession) -> ResponseModel:
    await crud_text2sql_table.delete(db, pk)
    await db.commit()
    return response_base.success(data='删除成功')


@router.post('/tables/{pk}/embed', summary='向量化表描述', dependencies=[DependsJwtAuth])
async def embed_table(pk: Annotated[int, Path(...)], db: CurrentSession) -> ResponseModel:
    ok = await text2sql_service.embed_table(db, pk)
    if not ok:
        return response_base.fail(message='向量化失败，请先填写表的中文描述')
    return response_base.success(data='向量化成功')


# ── 字段元数据 ────────────────────────────────────────────────────────────────

@router.get('/tables/{pk}/columns', summary='获取表的字段列表', dependencies=[DependsJwtAuth])
async def get_columns(pk: Annotated[int, Path(...)], db: CurrentSession) -> ResponseModel:
    columns = await crud_text2sql_column.get_by_table(db, pk)
    data = [TableColumnResponse.model_validate(c, from_attributes=True).model_dump() for c in columns]
    return response_base.success(data=data)


@router.put('/columns/{pk}', summary='更新字段元数据', dependencies=[DependsJwtAuth])
async def update_column(
    pk: Annotated[int, Path(...)], obj: UpdateColumnParam, db: CurrentSession
) -> ResponseModel:
    await crud_text2sql_column.update(db, pk, obj)
    await db.commit()
    return response_base.success(data='更新成功')


# ── Few-shot 示例 ────────────────────────────────────────────────────────────

@router.get('/examples', summary='获取示例列表', dependencies=[DependsJwtAuth, DependsPagination])
async def get_examples(db: CurrentSession) -> ResponseModel:
    stmt = crud_text2sql_example.get_list()
    page_data = await paging_data(db, stmt, ExampleResponse)
    return response_base.success(data=page_data)


@router.post('/examples', summary='新增 Few-shot 示例', dependencies=[DependsJwtAuth])
async def create_example(request: Request, obj: CreateExampleParam, db: CurrentSession) -> ResponseModel:
    from backend.app.admin.model.sys_text2sql_example import Text2SQLExample
    user_id = request.user.id
    example = Text2SQLExample(question=obj.question, sql=obj.sql, source='manual', create_user=user_id)
    db.add(example)
    await db.commit()
    await db.refresh(example)
    await text2sql_service.embed_example(db, example.id)
    return response_base.success(data=ExampleResponse.model_validate(example, from_attributes=True).model_dump())


@router.delete('/examples/{pk}', summary='删除示例', dependencies=[DependsJwtAuth])
async def delete_example(pk: Annotated[int, Path(...)], db: CurrentSession) -> ResponseModel:
    await crud_text2sql_example.delete(db, pk)
    await db.commit()
    return response_base.success(data='删除成功')


@router.post('/examples/from-feedback/{log_id}', summary='将反馈转为 Few-shot 示例', dependencies=[DependsJwtAuth])
async def create_example_from_feedback(
    request: Request, log_id: Annotated[int, Path(...)], db: CurrentSession
) -> ResponseModel:
    user_id = request.user.id
    example = await text2sql_service.create_example_from_feedback(db, log_id, user_id)
    if not example:
        return response_base.fail(message='该记录不存在或未包含用户提供的正确SQL')
    return response_base.success(data=ExampleResponse.model_validate(example, from_attributes=True).model_dump())
