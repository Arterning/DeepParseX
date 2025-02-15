#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime

from pydantic import ConfigDict

from backend.common.schema import SchemaBase


class SubjectSchemaBase(SchemaBase):
    
    name: str

    


class CreateSubjectParam(SubjectSchemaBase):
    pass


class UpdateSubjectParam(SubjectSchemaBase):
    pass


class GetSubjectListDetails(SubjectSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    
    created_time: datetime
    updated_time: datetime | None = None
    