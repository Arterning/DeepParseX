#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime

from pydantic import ConfigDict

from backend.common.schema import SchemaBase


class UploadTaskSchemaBase(SchemaBase):
    
    name: str

    
    status: str

    


class CreateUploadTaskParam(UploadTaskSchemaBase):
    pass


class UpdateUploadTaskParam(UploadTaskSchemaBase):
    pass


class GetUploadTaskListDetails(UploadTaskSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    
    created_time: datetime
    updated_time: datetime | None = None
    


class GetUploadTaskDetails(UploadTaskSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    
    created_time: datetime
    updated_time: datetime | None = None
    