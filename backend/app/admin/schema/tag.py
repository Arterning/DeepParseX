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


class GetTagListDetails(TagSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    
    created_time: datetime
    updated_time: datetime | None = None
    