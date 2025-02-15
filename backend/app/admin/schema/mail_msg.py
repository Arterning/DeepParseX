#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime

from pydantic import ConfigDict

from backend.common.schema import SchemaBase


class MailMsgSchemaBase(SchemaBase):
    
    name: str

    


class CreateMailMsgParam(MailMsgSchemaBase):
    pass


class UpdateMailMsgParam(MailMsgSchemaBase):
    pass


class GetMailMsgListDetails(MailMsgSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    
    created_time: datetime
    updated_time: datetime | None = None
    