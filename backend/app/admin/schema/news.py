#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime

from pydantic import ConfigDict

from backend.common.schema import SchemaBase


class NewsSchemaBase(SchemaBase):
    
    name: str
    summary: str  | None = None
    news_type: str  | None = None
    source: str  | None = None
    organization: str  | None = None
    author: str  | None = None
    time: str  | None = None
    location: str  | None = None
    tag: str  | None = None
    person: str  | None = None
    detail:str | None = None

    


class CreateNewsParam(NewsSchemaBase):
    pass


class UpdateNewsParam(NewsSchemaBase):
    pass


class GetNewsListDetails(NewsSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    
    created_time: datetime
    updated_time: datetime | None = None
    