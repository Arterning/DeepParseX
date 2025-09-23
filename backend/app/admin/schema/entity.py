#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
from typing import Dict, Any, Optional, List

from pydantic import ConfigDict

from backend.common.schema import SchemaBase


class EntitySchemaBase(SchemaBase):
    name: str
    description: str | None = None
    entity_type: str | None = None
    properties: Optional[Dict[str, Any]] = None
    


class CreateEntityParam(EntitySchemaBase):
    pass


class UpdateEntityParam(EntitySchemaBase):
    pass

class EntityDocs(SchemaBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
    title: str
    name: str | None = None
    type: str | None = None
    doc_time: datetime | None = None


class GetEntityListDetails(EntitySchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    relationships: Optional[Any] = None  # 关系数据
    docs: Optional[List[EntityDocs]] = None  # 关联的文档列表
    
    created_time: datetime
    updated_time: datetime | None = None
    
class GetEntityDetails(EntitySchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    
    created_time: datetime
    updated_time: datetime | None = None