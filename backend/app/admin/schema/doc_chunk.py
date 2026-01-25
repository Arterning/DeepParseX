#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
from pydantic import ConfigDict

from backend.common.schema import SchemaBase


class SysDocChunkSchemaBase(SchemaBase):
    doc_id: int
    chunk_index: int
    chunk_text: str | None = None
    chunk_translation: str | None = None


class CreateSysDocChunkParam(SysDocChunkSchemaBase):
    pass


class UpdateSysDocChunkParam(SysDocChunkSchemaBase):
    pass


class GetSysDocChunkListDetails(SysDocChunkSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_time: datetime
    updated_time: datetime | None = None
