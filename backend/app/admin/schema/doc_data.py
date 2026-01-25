#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
from pydantic import ConfigDict

from backend.common.schema import SchemaBase


class SysDocDataSchemaBase(SchemaBase):
    row: dict
    doc_id: int


class CreateSysDocDataParam(SysDocDataSchemaBase):
    pass


class UpdateSysDocDataParam(SysDocDataSchemaBase):
    pass


class GetSysDocDataListDetails(SysDocDataSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_time: datetime
    updated_time: datetime | None = None
