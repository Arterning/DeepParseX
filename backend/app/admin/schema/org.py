#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
from pydantic import ConfigDict
from backend.common.schema import SchemaBase

class UpdateOrgParam(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    org_name:str
    org_file_nums:int | None = None
    org_assets_nums:int | None = None
    org_desc:str | None = None

class OrgParam(UpdateOrgParam):
    assets: list[int] | None = None
    docs: list[int] | None = None

class GetOrgListDetails(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    org_name:str
    org_file_nums:int
    org_assets_nums:int
    org_desc:str
    created_time: datetime
    updated_time: datetime | None = None

class GetOrgDetail(UpdateOrgParam):
    id: int
    assets: list[dict] | None = None
    docs: list[dict] | None = None
