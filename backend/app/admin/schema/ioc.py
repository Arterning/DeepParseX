#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Literal

from pydantic import ConfigDict

from backend.common.schema import SchemaBase

IocType = Literal['ip', 'domain', 'url', 'md5', 'sha1', 'sha256', 'email', 'cve']


class IocSchemaBase(SchemaBase):
    ioc_type: str
    value: str
    context: str | None = None
    is_defanged: bool = False
    status: int = 0
    doc_id: int | None = None
    entity_id: int | None = None


class CreateIocParam(IocSchemaBase):
    pass


class UpdateIocStatusParam(SchemaBase):
    status: int  # 0=待确认 1=有效 2=误报


class GetIocListDetails(IocSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_time: datetime
    updated_time: datetime | None = None


class GetIocDetail(IocSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_time: datetime
    updated_time: datetime | None = None


class PromoteIocToEntityParam(SchemaBase):
    entity_type: str
    description: str | None = None
