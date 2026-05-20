#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Any

from pydantic import ConfigDict

from backend.common.schema import SchemaBase


# ── 表元数据 ────────────────────────────────────────────────────────────────

class ImportTablesParam(SchemaBase):
    table_names: list[str]


class UpdateTableParam(SchemaBase):
    display_name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class TableColumnResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    column_name: str
    data_type: str | None = None
    description: str | None = None
    sample_values: list | None = None
    is_sensitive: bool
    ordinal_position: int | None = None


class TableResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    schema_name: str
    table_name: str
    display_name: str | None = None
    description: str | None = None
    is_active: bool
    has_embedding: bool = False
    created_time: datetime
    updated_time: datetime | None = None


class TableDetailResponse(TableResponse):
    columns: list[TableColumnResponse] = []


class AvailableTableItem(SchemaBase):
    schema_name: str
    table_name: str
    is_imported: bool
    whitelisted_id: int | None = None


# ── 字段元数据 ───────────────────────────────────────────────────────────────

class UpdateColumnParam(SchemaBase):
    description: str | None = None
    sample_values: list | None = None
    is_sensitive: bool | None = None


# ── Few-shot 示例 ────────────────────────────────────────────────────────────

class CreateExampleParam(SchemaBase):
    question: str
    sql: str


class ExampleResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    question: str
    sql: str
    source: str
    has_embedding: bool = False
    created_time: datetime


# ── 查询 ─────────────────────────────────────────────────────────────────────

class QueryParam(SchemaBase):
    question: str
    session_id: str | None = None
    clarification_answer: str | None = None


class ClarificationOption(SchemaBase):
    label: str
    value: str


class QueryResponse(SchemaBase):
    log_id: int | None = None
    sql: str | None = None
    columns: list[str] | None = None
    rows: list[list[Any]] | None = None
    summary: str | None = None
    warning: str | None = None
    execution_time_ms: int | None = None
    clarification: 'ClarificationResult | None' = None


class ClarificationResult(SchemaBase):
    prompt: str
    options: list[ClarificationOption]


# ── 反馈 ─────────────────────────────────────────────────────────────────────

class FeedbackParam(SchemaBase):
    log_id: int
    rating: int
    correct_sql: str | None = None


# ── 查询历史 ──────────────────────────────────────────────────────────────────

class QueryLogResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    question: str
    generated_sql: str | None = None
    status: str
    error_message: str | None = None
    row_count: int | None = None
    execution_time_ms: int | None = None
    retry_count: int
    feedback: int | None = None
    create_user: int | None = None
    created_time: datetime
