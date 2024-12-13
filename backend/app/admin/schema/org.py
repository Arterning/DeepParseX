#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
from pydantic import ConfigDict
from backend.common.schema import SchemaBase



class OrgParam(SchemaBase):
    org_name:str
    org_file_nums:int
    org_assets_nums:int
    org_desc:str

class GetOrgListDetails(OrgParam):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_time: datetime
    updated_time: datetime | None = None