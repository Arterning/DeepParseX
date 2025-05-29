#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from fastapi import APIRouter
from datetime import datetime
from typing import Annotated
from backend.common.response.response_schema import response_base
from backend.app.admin.service.upload_service import upload_service
import os
from fastapi import File, UploadFile, Form, Request
from pathlib import Path
from backend.common.log import log
from backend.common.security.jwt import DependsJwtAuth

import os

router = APIRouter()


@router.post("/", summary='上传文件', dependencies=[DependsJwtAuth])
async def upload_file(
    file: UploadFile = File(...), 
    last_modified: Annotated[datetime| None, Form(...)] = None,
    size: Annotated[int | None, Form(...)] = None,
    request: Request = None,
):
    meta = {
        "last_modified": last_modified,
        "size": size,
    }
    # print("meta", meta)
    # print("request", request.user)
    user = request.user
    doc = await upload_service.save_file(file, meta, user)
    resp = {
        "id": doc.id
    }
    return response_base.success(data=resp)
