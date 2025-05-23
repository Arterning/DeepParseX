#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
from pydantic import ConfigDict

from backend.common.schema import SchemaBase


class SysDocSchemaBase(SchemaBase):
    title: str
    name: str | None = None
    type: str | None = None
    file_suffix: str | None = None
    content: str | None = None
    c_tokens: str | None = None
    desc: str | None = None
    file: str | None = None
    belong: int | None = None
    account_pwd:str | None = None

class GetSysDocPage(SchemaBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
    title: str
    name: str | None = None
    type: str | None = None
    desc: str | None = None
    # uuid: str | None = None
    created_time: datetime


class CreateSysDocParam(SysDocSchemaBase):
    uuid: str | None = None
    pass


class UpdateSysDocParam(SchemaBase):
    title: str | None = None
    name: str | None = None
    type: str | None = None
    content: str | None = None
    desc: str | None = None



class GetSysDocListDetails(SysDocSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_time: datetime
    updated_time: datetime | None = None


class GetDocSPO(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_time: datetime
    updated_time: datetime | None = None
    subject: str | None = None
    predicate: str | None = None
    object: str | None = None

class GetDocDetail(SysDocSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_time: datetime
    updated_time: datetime | None = None
    doc_data: list[dict]
    doc_spos: list[GetDocSPO]
    graph_data: dict
