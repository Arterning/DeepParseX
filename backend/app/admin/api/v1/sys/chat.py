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
    time1 = time.perf_counter()
    text_embed = await sys_doc_service.get_column_data('text_embed')
    time2 = time.perf_counter()
    print(f"数据库拿到向量    {time2-time1}")
    all_database = []
    for i in range(len(text_embed)):
        if text_embed[i] is not None:
            decoded_data = json.loads(text_embed[i])
            all_database += decoded_data
    all_database = json.dumps(all_database)
    time3 = time.perf_counter()
    print(f"向量拼接用时：      {time3-time2}")
    data = search_rag_inthedocker(text=obj.question, database_jsondata=all_database)
    time4 = time.perf_counter()
    print(f"RAG智能问答时间{time4 - time3}秒")
    return response_base.success(data=data)
    
    
