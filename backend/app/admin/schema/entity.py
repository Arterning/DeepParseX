#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
from typing import Dict, Any, Optional, List

from pydantic import ConfigDict

from backend.common.schema import SchemaBase


class AnalyzeEntitiesParam(SchemaBase):
    entity_ids: List[int]


class EntitySchemaBase(SchemaBase):
    name: str
    description: str | None = None
    entity_type: str | None = None
    properties: Optional[Dict[str, Any]] = None


class CreateEntityParam(EntitySchemaBase):
    pass


class UpdateEntityParam(EntitySchemaBase):
    pass


class ParseFileResponse(SchemaBase):
    """解析文件返回结果"""
    headers: List[str]
    preview_rows: List[Dict[str, Any]]
    total_rows: int
    rows: List[List[Any]]


class FieldMappingItem(SchemaBase):
    """字段映射项"""
    target: str  # name / description / entity_type / properties / ignore
    field_name: str | None = None  # 当 target 为 properties 时，为自定义属性名


class BatchImportParam(SchemaBase):
    """批量导入参数"""
    file_headers: List[str]
    field_mapping: Dict[str, FieldMappingItem]
    entity_type_name: str | None = None
    entity_type_description: str | None = None
    create_entity_type: bool = False
    rows: List[List[Any]]


class BatchImportResult(SchemaBase):
    """批量导入结果"""
    total: int
    created: int
    errors: List[Dict[str, Any]]

class EntityDocs(SchemaBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
    title: str
    name: str | None = None
    type: str | None = None
    content: str | None = None
    doc_time: datetime | None = None


class GetEntityListDetails(EntitySchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    
    created_time: datetime
    updated_time: datetime | None = None
    
class GetEntityDetails(EntitySchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    relationships: Optional[Any] = None  # 关系数据
    docs: Optional[List[EntityDocs]] = None  # 关联的文档列表
    starred_ids: Optional[List[int]] = None  # 收藏夹ID列表
    matched_chunks: Optional[List[Dict[str, Any]]] = None  # 包含实体名称的文本片段
    profile: Optional[str] = None  # 实体画像
    timeline: Optional[List[Dict[str, Any]]] = None  # 时间轴脉络

    created_time: datetime
    updated_time: datetime | None = None