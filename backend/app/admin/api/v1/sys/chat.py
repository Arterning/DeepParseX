#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from typing import Annotated
from backend.app.admin.schema.chat import ChatParam
from backend.common.response.response_schema import ResponseModel, response_base
from backend.app.admin.service.doc_service import sys_doc_service
from fastapi import APIRouter, Request
from backend.common.log import log
from backend.utils.doc_utils import search_rag_inthedocker
import time

router = APIRouter()


@router.post('', summary='对话')
async def chat(obj: ChatParam, request: Request) -> ResponseModel:
    data = await search_rag_inthedocker(text=obj.question)
    return response_base.success(data=data)
    
    
