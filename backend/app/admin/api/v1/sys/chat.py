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
        "answer": "回答内容，使用 [1]、[2] 标注引用来源",
        "references": [
            {
                "ref_index": 1,
                "doc_id": 123,
                "doc_name": "文档名称",
                "content_preview": "引用内容摘要"
            }
        ]
    }
    """
    data = await chat_service.rag_chat(obj=obj)
    return response_base.success(data=data)
    
    
