#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime

from pydantic import ConfigDict

from backend.common.schema import SchemaBase


class PersonRelationSchemaBase(SchemaBase):
    person_id: int | None = None
    other_id: int | None = None
    relation_type: str | None = None
    weight: int | None = None
    description : str | None = None



class CreatePersonRelationParam(PersonRelationSchemaBase):
    pass


class UpdatePersonRelationParam(PersonRelationSchemaBase):
    pass


class GetPersonRelationListDetails(PersonRelationSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    
    created_time: datetime
    updated_time: datetime | None = None
    

class GetPersonRelationDetails(PersonRelationSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    
    created_time: datetime
    updated_time: datetime | None = None