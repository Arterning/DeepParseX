#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
from pydantic import ConfigDict

from backend.common.schema import SchemaBase
from backend.app.admin.schema.mail_msg import GetMailMsgDetails

class SysDocSchemaBase(SchemaBase):
    title: str
    name: str | None = None
    type: str | None = None
    file_suffix: str | None = None
    content: str | None = None
    doc_tokens: str | None = None
    desc: str | None = None
    file: str | None = None
    belong: int | None = None
    doc_time: datetime | None = None
    size: int | None = None
    source: str | None = None
    status: int | None = None
    dept_id: int | None = None
    created_by: int | None = None
    created_user: str | None = None
    

class GetSysDocPage(SysDocSchemaBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
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
    email_msg: GetMailMsgDetails | None = None
