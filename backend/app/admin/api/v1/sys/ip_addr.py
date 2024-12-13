#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import json
from typing import Annotated
from backend.app.admin.schema.chat import ChatParam
from backend.common.response.response_schema import ResponseModel, response_base
from backend.app.admin.service.assets_service import assets_service
from backend.app.admin.service.doc_service import sys_doc_service
from fastapi import APIRouter, Body, Path
from backend.common.log import log
from backend.utils.doc_utils import request_rag_01
from backend.common.security.jwt import DependsJwtAuth
from backend.utils.doc_utils import get_ipaddr
from backend.database.db_pg import async_db_session
from backend.app.admin.schema.assets import AssetsParam
router = APIRouter()

@router.post('',summary="获取文件中的ip地址",dependencies=[DependsJwtAuth])
async def get_ip_addr(pk: Annotated[list[int],Body(...),]) -> ResponseModel:
    # 拿到id之后先查到所有content
    docs_select = await sys_doc_service.get_select(ids=pk)
    async with async_db_session() as db:
        result = await db.execute(docs_select)

    doc_list = result.scalars().all()  
    content_list = [doc.content for doc in doc_list]
   
    loop = asyncio.get_running_loop()
    ip_list = await loop.run_in_executor(None,get_ipaddr,content_list)
    
    if not ip_list:
        return response_base.success()

    asset_list = [AssetsParam(ip_addr=ip) for ip in ip_list]
    await assets_service.bulk_create(obj=asset_list)

    return response_base.success()

    

