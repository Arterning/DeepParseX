#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from typing import Annotated
from backend.app.admin.schema.chat import ChatParam
from backend.common.response.response_schema import ResponseModel, response_base
from backend.app.admin.service.chat_service import chat_service
from fastapi import APIRouter, Request
from backend.common.log import log
import time

router = APIRouter()


@router.post('', summary='对话')
async def chat(obj: ChatParam, request: Request) -> ResponseModel:
    data = await chat_service.rag_chat(text=obj.question)
    return response_base.success(data=data)
    
    
