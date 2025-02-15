#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime

from pydantic import ConfigDict

from backend.common.schema import SchemaBase


class NewsSchemaBase(SchemaBase):
    
    name: str

    


class CreateNewsParam(NewsSchemaBase):
    pass


class UpdateNewsParam(NewsSchemaBase):
    pass


class GetNewsListDetails(NewsSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    
    created_time: datetime
    updated_time: datetime | None = None
    