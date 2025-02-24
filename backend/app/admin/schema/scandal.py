#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional
from pydantic import ConfigDict
from backend.common.schema import SchemaBase
from datetime import datetime


class ScandalBase(SchemaBase):
    """黑料基础模型"""
    name: Optional[str] = None
    content: Optional[str] = None


class CreateScandal(ScandalBase):
    """创建黑料"""
    pass


class UpdateScandal(ScandalBase):
    """更新黑料"""
    pass

class PersonSchema(SchemaBase):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)

class GetScandalDetail(ScandalBase):
    id: int
    person: Optional[PersonSchema] = None

class GetScandalList(ScandalBase):
    """获取黑料列表"""
    id: int
    person: Optional[PersonSchema] = None
    created_time: datetime
    updated_time: datetime | None = None

    model_config = ConfigDict(from_attributes=True)