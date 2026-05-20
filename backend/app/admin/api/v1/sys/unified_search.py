#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from fastapi import APIRouter, Request

from backend.app.admin.schema.unified_search_schema import UnifiedSearchParam
from backend.app.admin.service.intent_service import detect_intent
from backend.app.admin.service.unified_search_service import unified_search_service
from backend.common.response.response_schema import ResponseModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db_pg import CurrentSession

router = APIRouter()


@router.post('/intent', summary='意图识别（快速预检测）', dependencies=[DependsJwtAuth])
async def get_intent(obj: UnifiedSearchParam) -> ResponseModel:
    intent = await detect_intent(obj.question)
    return response_base.success(data=intent.model_dump())


@router.post('/query', summary='统一多路检索问答', dependencies=[DependsJwtAuth])
async def unified_query(
    request: Request, obj: UnifiedSearchParam, db: CurrentSession
) -> ResponseModel:
    user_id = request.user.id
    result = await unified_search_service.query(
        question=obj.question,
        enabled_paths=obj.enabled_paths,
        user_id=user_id,
        db=db,
    )
    return response_base.success(data=result.model_dump())
