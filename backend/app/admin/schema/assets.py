#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
from pydantic import ConfigDict
from backend.common.schema import SchemaBase


class AssetsParam(SchemaBase):
    ip_addr: str
    assets_name:str | None = None
    assets_ports:list[str] | None = None
    assets_services:list[str] | None = None
    assets_desc:str | None = None
    assets_status:bool = False
    assets_remarks:str | None = None

class GetAssetListDetails(AssetsParam):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_time: datetime
    updated_time: datetime | None = None