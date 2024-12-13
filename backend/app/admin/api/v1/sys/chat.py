#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from typing import Annotated
from backend.app.admin.schema.chat import ChatParam
from backend.common.response.response_schema import ResponseModel, response_base
from backend.app.admin.service.doc_service import sys_doc_service
from fastapi import APIRouter
from backend.common.log import log
from backend.utils.doc_utils import request_rag_01

router = APIRouter()


@router.post('', summary='对话')
async def chat(obj:ChatParam) -> ResponseModel:
    
    text_embed = await sys_doc_service.get_column_data('text_embed')
    all_database = []
    for i in range(len(text_embed)):
        if text_embed[i] is not None:
            decoded_data = json.loads(text_embed[i])
            all_database += decoded_data
    all_database = json.dumps(all_database)
    data = request_rag_01(text=obj.question,database=all_database)
    return response_base.success(data=data)
    
