#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
from pydantic import ConfigDict, field_validator

from backend.common.schema import SchemaBase
from backend.app.admin.schema.mail_msg import GetMailMsgDetails

class SysDocSchemaBase(SchemaBase):
    title: str
    name: str | None = None
    type: str | None = None
    file_suffix: str | None = None
    content: str | None = None
    desc: str | None = None
    translation: str | None = None
    file: str | None = None
    belong: int | None = None
    doc_time: datetime | None = None
    size: int | None = None
    source: str | None = None
    status: int | None = None
    dept_id: int | None = None
    doc_dir_id: int | None = None
    created_by: int | None = None
    created_user: str | None = None
    

class GetTagSimple(SchemaBase):
    """简化的标签信息，用于列表展示"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class GetSysDocPage(SysDocSchemaBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
    created_time: datetime
    is_collected: bool = False
    tags: list[GetTagSimple] = []

    @field_validator('content', mode='before')
    @classmethod
    def truncate_content(cls, v: str | None) -> str | None:
        if v and len(v) > 500:
            return v[:500] + '...'
        return v


class CreateSysDocParam(SysDocSchemaBase):
    uuid: str | None = None
    tags: list[str] | None = []
    pass


class UpdateSysDocParam(SchemaBase):
    title: str | None = None
    name: str | None = None
    type: str | None = None
    content: str | None = None
    desc: str | None = None
    error_msg: str | None = None
    status: int | None = None
    tags: list[str] | None = []



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


class GetTagDetails(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_time: datetime
    updated_time: datetime | None = None

class GetDocEntity(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None = None
    entity_type: str | None = None
    properties: dict | None = None

class GetDocDetail(SysDocSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_time: datetime
    updated_time: datetime | None = None
    doc_data: list[dict]
    doc_spos: list[GetDocSPO]
    tags: list[GetTagDetails] | None = []
    graph_data: dict
    entities: list[GetDocEntity]
    email_msg: GetMailMsgDetails | None = None
    error_msg: str | None = None


class CollectDocParam(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    doc_id: int
    collection_id: int | None = None



class ParseEntityParams(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    entity_types: list[str] | None = None


class ExtractEntitiesParams(SchemaBase):
    """提取实体参数"""
    model_config = ConfigDict(from_attributes=True)
    entity_type_ids: list[int] 