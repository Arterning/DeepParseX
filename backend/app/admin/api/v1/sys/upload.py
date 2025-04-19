#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from fastapi import APIRouter

from backend.common.response.response_schema import response_base
from backend.app.admin.service.upload_service import upload_service
import os
from fastapi import File, UploadFile
from pathlib import Path
from backend.common.log import log

import os

router = APIRouter()


@router.post("/", summary='上传文件')
async def upload_file(file: UploadFile = File(...)):
    doc = await upload_service.save_file(file)
    resp = {
        "id": doc.id
    }
    return response_base.success(data=resp)
