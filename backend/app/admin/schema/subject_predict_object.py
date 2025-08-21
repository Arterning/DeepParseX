#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime

from pydantic import ConfigDict

from backend.common.schema import SchemaBase


class SubjectPredictObjectSchemaBase(SchemaBase):
    
    subject: str | None = None

    
    subject_type: str | None = None

    
    predicate: str | None = None

    
    object: str | None = None

    
    object_type: str | None = None

    
    doc_id: int | None = None

    


class CreateSubjectPredictObjectParam(SubjectPredictObjectSchemaBase):
    pass


class UpdateSubjectPredictObjectParam(SubjectPredictObjectSchemaBase):
    pass


class GetSubjectPredictObjectListDetails(SubjectPredictObjectSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    
    created_time: datetime
    updated_time: datetime | None = None
    


class GetSubjectPredictObjectDetails(SubjectPredictObjectSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    
    created_time: datetime
    updated_time: datetime | None = None
    