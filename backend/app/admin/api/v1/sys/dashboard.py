from typing import Annotated

from backend.common.security.jwt import DependsJwtAuth
from backend.common.response.response_schema import ResponseModel, response_base
from backend.app.admin.service.doc_service import sys_doc_service
from fastapi import APIRouter, Query, Request
from backend.utils.serializers import select_as_dict

router = APIRouter()


@router.get('/count', summary='获取首页面板数据',
    dependencies=[DependsJwtAuth]
 )
async def get_dashboard_index(request: Request) -> ResponseModel:
    user_id = request.user.id
    data = await sys_doc_service.get_count()
    return response_base.success(data=data)

