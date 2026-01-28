#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
from typing import List, Optional

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class EntityTypeSchemaBase(SchemaBase):
    name: str = Field(description='实体类型名称')
    description: Optional[str] = Field(None, description='实体类型描述')
    field_definition: Optional[List[str]] = Field(None, description='字段定义（字段名称数组）')


class CreateEntityTypeParam(EntityTypeSchemaBase):
    """创建实体类型参数"""
    pass


class UpdateEntityTypeParam(SchemaBase):
    """更新实体类型参数"""
    name: Optional[str] = Field(None, description='实体类型名称')
    description: Optional[str] = Field(None, description='实体类型描述')
    field_definition: Optional[List[str]] = Field(None, description='字段定义（字段名称数组）')


class GetEntityTypeListDetails(EntityTypeSchemaBase):
    """获取实体类型列表详情"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_time: datetime
    updated_time: Optional[datetime] = None


class GetEntityTypeDetails(GetEntityTypeListDetails):
    """获取实体类型详情"""
    pass
