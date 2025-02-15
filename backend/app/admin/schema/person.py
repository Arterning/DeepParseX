#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime

from pydantic import ConfigDict

from backend.common.schema import SchemaBase


class PersonSchemaBase(SchemaBase):
    
    name: str

    


class CreatePersonParam(PersonSchemaBase):
    pass


class UpdatePersonParam(PersonSchemaBase):
    pass


class GetPersonListDetails(PersonSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    
    created_time: datetime
    updated_time: datetime | None = None
    