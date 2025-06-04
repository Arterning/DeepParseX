#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime

from pydantic import ConfigDict

from backend.common.schema import SchemaBase


class StarCollectSchemaBase(SchemaBase):
    
    name: str

    description: str | None = None

    


class CreateStarCollectParam(StarCollectSchemaBase):
    pass


class UpdateStarCollectParam(StarCollectSchemaBase):
    pass


class GetStarDocs(SchemaBase):
    title: str
    name: str | None = None
    type: str | None = None
    id: int
    model_config = ConfigDict(from_attributes=True)


class GetStarCollectListDetails(StarCollectSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    docs: list[GetStarDocs] | None = []
    created_time: datetime
    updated_time: datetime | None = None
    


class GetStarCollectDetails(StarCollectSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    
    created_time: datetime
    updated_time: datetime | None = None
    