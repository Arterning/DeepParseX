#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Literal

from pydantic import ConfigDict

from backend.common.schema import SchemaBase


class CreateGeoPointParam(SchemaBase):
    doc_id: int | None = None
    ioc_id: int | None = None
    source_type: str
    lat: float | None = None
    lng: float | None = None
    altitude: float | None = None
    country: str | None = None
    city: str | None = None
    accuracy: str | None = None
    raw_exif: dict | None = None


class GetGeoPointListDetails(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    doc_id: int | None = None
    ioc_id: int | None = None
    source_type: str
    lat: float | None = None
    lng: float | None = None
    altitude: float | None = None
    country: str | None = None
    city: str | None = None
    accuracy: str | None = None
    created_time: datetime
