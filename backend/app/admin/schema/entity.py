#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
from typing import Dict, Any, Optional

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


class GetEntityListDetails(EntitySchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    relationships: Optional[Any] = None  # 关系数据
    
    created_time: datetime
    updated_time: datetime | None = None
    
class GetEntityDetails(EntitySchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    
    created_time: datetime
    updated_time: datetime | None = None