#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime

from pydantic import ConfigDict

from backend.common.schema import SchemaBase


class MailBoxSchemaBase(SchemaBase):
    
    name: str

    


class CreateMailBoxParam(MailBoxSchemaBase):
    pass


class UpdateMailBoxParam(MailBoxSchemaBase):
    pass


class GetMailBoxListDetails(MailBoxSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    
    created_time: datetime
    updated_time: datetime | None = None
    