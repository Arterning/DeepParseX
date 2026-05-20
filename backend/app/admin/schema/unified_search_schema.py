#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pydantic import ConfigDict

from backend.common.schema import SchemaBase


class IntentScores(SchemaBase):
    fulltext: float = 0.0
    rag: float = 0.0
    text_to_sql: float = 0.0
    graph: float = 0.0


class DocChunk(SchemaBase):
    doc_id: int | None = None
    doc_name: str | None = None
    content_preview: str


class SourceItem(SchemaBase):
    type: str  # "fulltext" | "rag" | "text_to_sql" | "graph"

    # fulltext / rag
    chunks: list[DocChunk] | None = None
    path_answer: str | None = None   # RAG 路径自身的答案

    # text_to_sql
    sql: str | None = None
    columns: list[str] | None = None
    rows: list[list] | None = None
    row_count: int | None = None
    sql_error: str | None = None

    # graph（骨架，暂未实现）
    entities: list[dict] | None = None
    relations: list[dict] | None = None


class UnifiedSearchParam(SchemaBase):
    question: str
    # None 表示由 AI 自动决定；传入列表则用用户指定的路径
    enabled_paths: list[str] | None = None


class UnifiedSearchResponse(SchemaBase):
    answer: str | None = None
    intent: IntentScores
    used_paths: list[str]
    sources: list[SourceItem]
    execution_time_ms: int | None = None
