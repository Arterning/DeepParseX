#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime

from pydantic import ConfigDict

from backend.common.schema import SchemaBase


class ChatSessionSchemaBase(SchemaBase):
    
    
    topic: str

    
    create_user: int | None = None


    


class CreateChatSessionParam(ChatSessionSchemaBase):
    created_time: datetime | None = None


class UpdateChatSessionParam(ChatSessionSchemaBase):
    update_user: int | None = None
    updated_time: datetime | None = None


class GetChatSessionListDetails(ChatSessionSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    
    created_time: datetime
    updated_time: datetime | None = None
    


class GetChatSessionDetails(ChatSessionSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    
    created_time: datetime
    updated_time: datetime | None = None
    