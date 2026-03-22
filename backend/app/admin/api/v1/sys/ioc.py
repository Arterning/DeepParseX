#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.app.admin.schema.ioc import GetIocListDetails, PromoteIocToEntityParam, UpdateIocStatusParam
from backend.app.admin.service.ioc_service import ioc_service
from backend.common.pagination import DependsPagination, paging_data
from backend.common.response.response_schema import ResponseModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db_pg import CurrentSession

router = APIRouter()


@router.get(
    '',
    summary='（条件）分页获取 IOC 列表',
    dependencies=[DependsJwtAuth, DependsPagination],
)
async def get_ioc_list(
    db: CurrentSession,
    doc_id: Annotated[int | None, Query(description='按来源文档筛选')] = None,
    ioc_type: Annotated[str | None, Query(description='类型: ip/domain/url/md5/sha1/sha256/email/cve')] = None,
    value: Annotated[str | None, Query(description='值模糊匹配')] = None,
    status: Annotated[int | None, Query(description='状态: 0=待确认 1=有效 2=误报')] = None,
) -> ResponseModel:
    ioc_select = await ioc_service.get_select(doc_id=doc_id, ioc_type=ioc_type, value=value, status=status)
    page_data = await paging_data(db, ioc_select, GetIocListDetails)
    return response_base.success(data=page_data)


@router.get('/{pk}', summary='获取 IOC 详情', dependencies=[DependsJwtAuth])
async def get_ioc(pk: Annotated[int, Path(...)]) -> ResponseModel:
    ioc = await ioc_service.get(pk=pk)
    return response_base.success(data=ioc)


@router.put('/{pk}/status', summary='更新 IOC 状态（确认/标记误报）', dependencies=[DependsJwtAuth])
async def update_ioc_status(
    pk: Annotated[int, Path(...)],
    obj: UpdateIocStatusParam,
) -> ResponseModel:
    count = await ioc_service.update_status(pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.post(
    '/{pk}/promote',
    summary='将 IOC 提升为知识图谱实体',
    dependencies=[DependsJwtAuth],
)
async def promote_ioc_to_entity(
    pk: Annotated[int, Path(...)],
    obj: PromoteIocToEntityParam,
) -> ResponseModel:
    """
    将指定 IOC 写入 sys_entity 并关联，使其可在知识图谱中展示。
    entity_type 建议值：IP地址 / 域名 / URL / 哈希值 / 邮箱 / CVE漏洞
    """
    entity_id = await ioc_service.promote_to_entity(pk=pk, obj=obj)
    return response_base.success(data={'entity_id': entity_id})


@router.post(
    '/re-extract/{doc_id}',
    summary='重新提取文档 IOC',
    dependencies=[DependsJwtAuth],
)
async def re_extract_ioc(doc_id: Annotated[int, Path(...)]) -> ResponseModel:
    """删除该文档已有 IOC 并重新提取"""
    count = await ioc_service.re_extract(doc_id=doc_id)
    return response_base.success(data={'count': count})


@router.delete(
    '',
    summary='（批量）删除 IOC',
    dependencies=[
        Depends(RequestPermission(':del')),
        DependsRBAC,
    ],
)
async def delete_ioc(pk: Annotated[list[int], Query(...)]) -> ResponseModel:
    count = await ioc_service.delete(pk=pk)
    if count > 0:
        return response_base.success()
    return response_base.fail()
