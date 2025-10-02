#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, Path, Query, Body

from backend.app.admin.schema.mail_box import CreateMailBoxParam, GetMailBoxDetails, GetMailBoxListDetails, UpdateMailBoxParam
from backend.app.admin.service.mail_box_service import mail_box_service
from backend.common.pagination import DependsPagination, paging_data
from backend.common.response.response_schema import ResponseModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db_pg import CurrentSession
from backend.utils.serializers import select_as_dict

router = APIRouter()



# 设置路由
@router.get('/ranking', summary='获取邮箱邮件数量排名', dependencies=[DependsJwtAuth])
async def get_mailbox_ranking_api(
    top_n: Annotated[int, Query(ge=1, le=100)] = 10,
    start_time: Annotated[datetime | None, Query()] = None,
    end_time: Annotated[datetime | None, Query()] = None
) -> ResponseModel:
    """
    获取邮箱邮件数量排名前N的邮箱

    :param top_n: 返回前N个邮箱，默认10个，范围1-100
    :param start_time: 开始时间
    :param end_time: 结束时间
    :return: 邮箱邮件数量排名列表
    """
    result = await mail_box_service.get_mailbox_ranking(
        top_n=top_n,
        start_time=start_time,
        end_time=end_time
    )
    return response_base.success(data=result)

@router.get('/provider-distribution', summary='获取邮箱类型分布', dependencies=[DependsJwtAuth])
async def get_email_provider_distribution_api(
    start_time: Annotated[datetime | None, Query()] = None,
    end_time: Annotated[datetime | None, Query()] = None
) -> ResponseModel:
    """
    获取邮箱类型分布统计

    :param start_time: 开始时间
    :param end_time: 结束时间
    :return: 邮箱类型分布数据
    """
    result = await mail_box_service.get_email_provider_distribution(
        start_time=start_time,
        end_time=end_time
    )
    return response_base.success(data=result)




@router.get('/{pk}', summary='获取详情', dependencies=[DependsJwtAuth])
async def get_mail_box(pk: Annotated[int, Path(...)]) -> ResponseModel:
    mail_box = await mail_box_service.get(pk=pk)
    data = GetMailBoxDetails(**select_as_dict(mail_box))
    return response_base.success(data=data)


@router.get(
    '',
    summary='（模糊条件）分页获取所有',
    dependencies=[
        DependsJwtAuth,
        DependsPagination,
    ],
)
async def get_pagination_mail_box(db: CurrentSession, name: Annotated[str | None, Query()] = None,) -> ResponseModel:
    mail_box_select = await mail_box_service.get_select(name=name)
    page_data = await paging_data(db, mail_box_select, GetMailBoxListDetails)
    return response_base.success(data=page_data)


@router.post(
    '',
    summary='创建',
    dependencies=[
        Depends(RequestPermission(':add')),
        DependsRBAC,
    ],
)
async def create_mail_box(obj: CreateMailBoxParam) -> ResponseModel:
    await mail_box_service.create(obj=obj)
    return response_base.success()


@router.put(
    '/{pk}',
    summary='更新',
    dependencies=[
        Depends(RequestPermission(':edit')),
        DependsRBAC,
    ],
)
async def update_mail_box(pk: Annotated[int, Path(...)], obj: UpdateMailBoxParam) -> ResponseModel:
    count = await mail_box_service.update(pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete(
    '',
    summary='（批量）删除',
    dependencies=[
        Depends(RequestPermission(':del')),
        DependsRBAC,
    ],
)
async def delete_mail_box(pk: Annotated[list[int], Query(...)]) -> ResponseModel:
    count = await mail_box_service.delete(pk=pk)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.post(
    '/analyze-relationships',
    summary='分析邮箱关系',
    dependencies=[DependsJwtAuth],
)
async def analyze_mailbox_relationships(
    mailboxes: Annotated[list[str], Body(...)],
    start_time: Annotated[datetime | None, Body()] = None,
    end_time: Annotated[datetime | None, Body()] = None,
    max_layers: Annotated[int, Body()] = 3,
    reference_time: Annotated[datetime | None, Body()] = None
) -> ResponseModel:
    """
    分析邮箱之间的关系

    :param mailboxes: 邮箱地址列表
    :param start_time: 开始时间
    :param end_time: 结束时间
    :param max_layers: 最大分析层级，默认3层
    :param reference_time: 时间权重计算的基准时间，默认为查询时间
    :return: 包含nodes和edges的图结构
    """
    result = await mail_box_service.analyze_mailbox_relationships(
        mailboxes=mailboxes,
        start_time=start_time,
        end_time=end_time,
        max_layers=max_layers,
        reference_time=reference_time
    )
    return response_base.success(data=result)
