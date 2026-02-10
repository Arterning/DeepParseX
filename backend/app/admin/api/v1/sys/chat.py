#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from typing import Annotated
from backend.app.admin.schema.chat import ChatParam, IdParam, TranslateParam
from backend.common.response.response_schema import ResponseModel, response_base
from backend.app.admin.service.chat_service import chat_service
from fastapi import APIRouter, Request
from backend.common.log import log
import time

router = APIRouter()


@router.post('', summary='对话')
async def chat(obj: ChatParam, request: Request) -> ResponseModel:
    """
    RAG 对话接口

    返回数据格式:
    {
        "answer": "回答内容（包含超链接的HTML字符串）",
        "chunks": [
            {
                "chunk_id": "文本片段UUID",
                "chunk_text": "文本片段内容",
                "doc_id": "文档ID",
                "doc_name": "文档名称"
            },
            ...
        ]
    }
    """
    data = await chat_service.rag_chat(obj=obj)
    return response_base.success(data=data)
    
    
