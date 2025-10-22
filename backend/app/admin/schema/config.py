#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class ConfigSchemaBase(SchemaBase):
    login_title: str = Field(default='登陆 DeepParseX')
    login_sub_title: str = Field(default='DeepParseX')
    footer: str = Field(default='DeepParseX')
    logo: str = Field(default='Arco')
    system_title: str = Field(default='Arco')
    system_comment: str = Field(
        default='强大的多模态文档解析与知识管理平台'
    )
    settings: dict = Field(default={})


class CreateConfigParam(ConfigSchemaBase):
    pass


class UpdateConfigParam(ConfigSchemaBase):
    pass


class GetConfigListDetails(ConfigSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_time: datetime
    updated_time: datetime | None = None
