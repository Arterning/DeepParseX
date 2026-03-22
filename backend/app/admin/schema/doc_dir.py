#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class SysDocDirSchemaBase(SchemaBase):
    name: str = Field(min_length=1, max_length=255)
    parent_id: int | None = None
    sort: int | None = Field(default=0, ge=0)
    remark: str | None = None


class CreateDocDirParam(SysDocDirSchemaBase):
    pass


class UpdateDocDirParam(SysDocDirSchemaBase):
    pass


class GetDocDirListDetails(SysDocDirSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_time: datetime | None = None
    children: list['GetDocDirListDetails'] | None = []
