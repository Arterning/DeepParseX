#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime

from pydantic import ConfigDict

from backend.common.schema import SchemaBase


class SocialAccountPostSchemaBase(SchemaBase):
    
    name: str
    time: datetime | None = None

    


class CreateSocialAccountPostParam(SocialAccountPostSchemaBase):
    pass


class UpdateSocialAccountPostParam(SocialAccountPostSchemaBase):
    pass


class GetSocialAccountPostListDetails(SocialAccountPostSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    
    created_time: datetime
    updated_time: datetime | None = None
    
class GetSocialAccountPostDetails(SocialAccountPostSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    
    created_time: datetime
    updated_time: datetime | None = None