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
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db_pg import async_db_session
from backend.app.admin.schema.assets import AssetsParam
import ipaddress
import re

router = APIRouter()

import re
import ipaddress

def extract_valid_ips(text):
    # 匹配潜在的 IPv4 地址
    ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
    potential_ips = re.findall(ip_pattern, text)
    
    # 使用 ipaddress 模块验证合法性，并过滤掉包含 255 和 0 的 IP 地址
    valid_ips = set()
    for ip in potential_ips:
        try:
            # 验证 IP 地址是否合法
            ip_obj = ipaddress.ip_address(ip)
            
            # 过滤掉包含 255 或 0 的 IP 地址
            if '0' not in ip.split('.') and '255' not in ip.split('.'):
                valid_ips.add(ip)
        except ValueError:
            # 非法 IP 地址会引发 ValueError，跳过
            continue
    
    return list(valid_ips)


@router.post('',summary="获取文件中的ip地址",dependencies=[DependsJwtAuth])
async def get_ip_addr(pk: Annotated[list[int],Body(...),]) -> ResponseModel:
    # 拿到id之后先查到所有content
    docs_select = await sys_doc_service.get_select(ids=pk)
    async with async_db_session() as db:
        result = await db.execute(docs_select)

    doc_list = result.scalars().all()  
    content_list = [doc.content for doc in doc_list]
    content = "\n".join(content_list)
    ip_list = extract_valid_ips(content)
    
    if not ip_list:
        return response_base.success()

    asset_list = [AssetsParam(ip_addr=ip) for ip in ip_list]
    await assets_service.bulk_create(obj=asset_list)

    return response_base.success()

    

