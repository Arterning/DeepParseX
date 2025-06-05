#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime

from pydantic import ConfigDict

from backend.common.schema import SchemaBase


class TagSchemaBase(SchemaBase):
    name: str
    create_user: int | None = None

    


class CreateTagParam(TagSchemaBase):
    pass


class UpdateTagParam(TagSchemaBase):
    update_user: int | None = None
    pass


class GetStarDocs(SchemaBase):
    title: str
    name: str | None = None
    type: str | None = None
    id: int
    model_config = ConfigDict(from_attributes=True)

class GetTagListDetails(TagSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    docs: list[GetStarDocs] | None = []
    created_time: datetime
    updated_time: datetime | None = None
    