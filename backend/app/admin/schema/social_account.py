#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime

from pydantic import ConfigDict

from backend.common.schema import SchemaBase


class SocialAccountSchemaBase(SchemaBase):
    
    name: str
    social_name: str | None = None
    social_account: str | None = None
    country: str | None = None
    gender: str | None = None
    political: str | None = None
    other_info: str | None = None

    


class CreateSocialAccountParam(SocialAccountSchemaBase):
    pass


class UpdateSocialAccountParam(SocialAccountSchemaBase):
    pass


class GetSocialAccountListDetails(SocialAccountSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    
    created_time: datetime
    updated_time: datetime | None = None
    

class GetSocialAccountDetails(SocialAccountSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    
    created_time: datetime
    updated_time: datetime | None = None