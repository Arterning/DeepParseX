#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime, date
from pydantic import ConfigDict

from backend.common.schema import SchemaBase


class BriefingSchemaBase(SchemaBase):
    title: str | None = None
    date: datetime | None = None
    summary: str | None = None
    content: str | None = None
    key_points: list | None = None
    categories: dict | None = None
    source_count: int | None = None
    doc_ids: list | None = None
    status: int | None = None
    error_msg: str | None = None
    llm_model: str | None = None
    generation_time: datetime | None = None


class GetBriefingPage(BriefingSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_time: datetime


class GetBriefingDetail(BriefingSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_time: datetime
    updated_time: datetime | None = None
