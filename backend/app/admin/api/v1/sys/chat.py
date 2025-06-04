#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from typing import Annotated
from backend.app.admin.schema.chat import ChatParam, IdParam
from backend.common.response.response_schema import ResponseModel, response_base
from backend.app.admin.service.chat_service import chat_service
from fastapi import APIRouter, Request
from backend.common.log import log
import time

router = APIRouter()


@router.post('', summary='对话')
async def chat(obj: ChatParam, request: Request) -> ResponseModel:
    data = await chat_service.rag_chat(obj=obj)
    return response_base.success(data=data)
    
    
# generate_summary
@router.post('/generate_summary', summary='生成摘要')
async def generate_summary(obj: IdParam, request: Request) -> ResponseModel:
    data = await chat_service.generate_summary(id=obj.id)
    return response_base.success(data=data)