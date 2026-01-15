#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Path, Query
from sqlalchemy import select, desc

from backend.app.admin.model.sys_briefing import Briefing
from backend.app.admin.schema.briefing import GetBriefingPage, GetBriefingDetail
from backend.common.pagination import DependsPagination, paging_data
from backend.common.response.response_schema import ResponseModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db_pg import CurrentSession
from backend.utils.serializers import select_as_dict

router = APIRouter()


@router.get(
    '',
    summary='分页获取简报列表',
    dependencies=[
        DependsJwtAuth,
        DependsPagination,
    ],
)
async def get_pagination_briefing(
    db: CurrentSession,
    title: Annotated[str | None, Query(description='简报标题')] = None,
    status: Annotated[int | None, Query(description='状态(0生成中 1已完成 2失败)')] = None,
    date_start: Annotated[str | None, Query(description='开始日期')] = None,
    date_end: Annotated[str | None, Query(description='结束日期')] = None,
) -> ResponseModel:
    """
    分页获取简报列表

    - **title**: 简报标题模糊搜索
    - **status**: 状态筛选 (0=生成中, 1=已完成, 2=失败)
    - **date_start**: 开始日期 (YYYY-MM-DD)
    - **date_end**: 结束日期 (YYYY-MM-DD)
    """
    stmt = select(Briefing).order_by(desc(Briefing.created_time))

    if title:
        stmt = stmt.where(Briefing.title.ilike(f'%{title}%'))
    if status is not None:
        stmt = stmt.where(Briefing.status == status)
    if date_start:
        stmt = stmt.where(Briefing.date >= date_start)
    if date_end:
        stmt = stmt.where(Briefing.date <= date_end)

    page_data = await paging_data(db, stmt, GetBriefingPage)
    return response_base.success(data=page_data)


@router.get(
    '/{pk}',
    summary='获取简报详情',
    dependencies=[DependsJwtAuth],
)
async def get_briefing_detail(
    db: CurrentSession,
    pk: Annotated[int, Path(description='简报ID')],
) -> ResponseModel:
    """获取简报详情"""
    result = await db.execute(
        select(Briefing).where(Briefing.id == pk)
    )
    briefing = result.scalar_one_or_none()

    if not briefing:
        return response_base.fail(message='简报不存在')

    data = GetBriefingDetail(**select_as_dict(briefing))
    return response_base.success(data=data)


@router.delete(
    '',
    summary='批量删除简报',
    dependencies=[DependsJwtAuth],
)
async def delete_briefing(
    db: CurrentSession,
    pk: Annotated[list[int], Query(description='简报ID列表')],
) -> ResponseModel:
    """批量删除简报"""
    result = await db.execute(
        select(Briefing).where(Briefing.id.in_(pk))
    )
    briefings = result.scalars().all()

    if not briefings:
        return response_base.fail(message='简报不存在')

    for briefing in briefings:
        await db.delete(briefing)

    await db.commit()
    return response_base.success(message=f'成功删除 {len(briefings)} 条简报')
