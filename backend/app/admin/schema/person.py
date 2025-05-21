#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime

from pydantic import ConfigDict

from backend.common.schema import SchemaBase


class PersonSchemaBase(SchemaBase):
    
    name: str
    other_name: str | None = None
    gender: str | None = None
    organization: str | None = None
    position: str | None = None
    profession: str | None = None
    birth_date: datetime | None = None
    school: str | None = None
    
    


class CreatePersonParam(PersonSchemaBase):
    pass


class UpdatePersonParam(PersonSchemaBase):
    pass


class GetPersonListDetails(PersonSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    
    created_time: datetime
    updated_time: datetime | None = None
    

class GetPersonDetails(PersonSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int

    graphData: dict | None = None
    
    created_time: datetime
    updated_time: datetime | None = None
   