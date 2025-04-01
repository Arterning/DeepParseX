#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
from typing import Annotated
from backend.common.response.response_schema import ResponseModel, response_base
from backend.app.admin.service.doc_service import sys_doc_service
from fastapi import APIRouter, Body, Path
from backend.common.log import log
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db_pg import async_db_session
router = APIRouter()

@router.post('',summary="获取文件中的用户名和密码",dependencies=[DependsJwtAuth])
async def get_account_and_pwd(pk: Annotated[list[int],Body(...),]) -> ResponseModel:
    # 拿到id之后先查到所有content
    docs_select = await sys_doc_service.get_select(ids=pk)
    async with async_db_session() as db:
        result = await db.execute(docs_select)

    # 所有的docs
    doc_list = result.scalars().all()  
    content_list = [doc.content for doc in doc_list]
   
    loop = asyncio.get_running_loop()
    accounts = ""
    count = await sys_doc_service.update_account_pwd(pk=pk,accounts=accounts)
    if count > 0:
        return response_base.success()
    else :return response_base.fail()
    # 批量修改数据库
    

