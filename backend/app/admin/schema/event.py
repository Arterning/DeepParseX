#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime

from pydantic import ConfigDict

from backend.common.schema import SchemaBase


class EventSchemaBase(SchemaBase):
    
    name: str

    
    event_time: datetime

    


class CreateEventParam(EventSchemaBase):
    pass


class UpdateEventParam(EventSchemaBase):
    pass


class GetEventListDetails(EventSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    
    created_time: datetime
    updated_time: datetime | None = None
    