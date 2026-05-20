#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from typing import Sequence
from datetime import datetime, timedelta
from sqlalchemy import bindparam, select, Select, text, desc, and_, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model import SysDoc
from backend.app.admin.schema.doc import CreateSysDocParam, UpdateSysDocParam


class CRUDSysDoc(CRUDPlus[SysDoc]):
    async def get(self, db: AsyncSession, pk: int) -> SysDoc | None:
        """
        获取 SysDoc

        :param db:
        :param pk:
        :return:
        """
        where = [self.model.id == pk]
        doc = await db.execute(
            select(self.model)
            .options(selectinload(self.model.doc_data))
            .options(selectinload(self.model.email_msg))
            .options(selectinload(self.model.doc_spos))
            .options(selectinload(self.model.tags))
            .options(selectinload(self.model.entities))
            .options(selectinload(self.model.doc_chunks))
            .where(*where)
        )
        return doc.scalars().first()

    async def get_list(self, name: str = None, doc_type: list[str] = None,
                       title: str = None, source: str = None,
                        content: str = None, ids: list[int] = None,
                        start_time: str = None, end_time :str = None,
                        current_user_id: int = None, tag_ids: list[int] = None,
                        doc_dir_id: int = None, status: int = None
                        ) -> Select:
        """
        获取 SysDoc 列表
        :param current_user_id: 当前登录用户ID，用于权限过滤
        :param tag_ids: 标签ID列表，用于筛选
        :return:
        """
        from backend.app.admin.model.sys_tag_doc import sys_tag_doc

        where_list = []
        stmt = (
            select(self.model)
            .options(selectinload(self.model.tags))
            .order_by(desc(self.model.created_time))
        )
        
        # 只有指定了current_user_id时，才进行用户权限过滤
        if current_user_id is not None:
            where_list.append(self.model.created_by == current_user_id)
        
        if title is not None and title != '':
            where_list.append(self.model.title.like(f'%{title}%'))
        if name is not None and name != '':
            where_list.append(self.model.name.like(f'%{name}%'))
        if doc_type is not None and len(doc_type) > 0:
            where_list.append(self.model.type.in_(doc_type))
        if content is not None and content != '':
            where_list.append(self.model.content.like(f'%{content}%'))
        if source is not None and source != '':
            where_list.append(self.model.source.like(f'%{source}%'))
        if start_time:
            start_dt = datetime.strptime(start_time, '%Y-%m-%d')
            where_list.append(self.model.doc_time >= start_dt)
        if end_time:
             # 将字符串转换为datetime对象，并设置时间为当天23:59:59
            end_dt = datetime.strptime(end_time, '%Y-%m-%d') + timedelta(hours=23, minutes=59, seconds=59)
            where_list.append(self.model.doc_time <= end_dt)
        if ids is not None:
            where_list.append(self.model.id.in_(ids))
        # 标签过滤：查询同时包含所有指定标签的文档
        if tag_ids is not None and len(tag_ids) > 0:
            # 使用子查询找出包含所有指定标签的文档ID
            subquery = (
                select(sys_tag_doc.c.doc_id)
                .where(sys_tag_doc.c.tag_id.in_(tag_ids))
                .group_by(sys_tag_doc.c.doc_id)
                .having(func.count(sys_tag_doc.c.tag_id.distinct()) == len(tag_ids))
            )
            where_list.append(self.model.id.in_(subquery))
        if doc_dir_id is not None:
            where_list.append(self.model.doc_dir_id == doc_dir_id)
        if status is not None:
            where_list.append(self.model.status == status)
        if where_list:
            stmt = stmt.where(and_(*where_list))
        return stmt

    async def get_all(self, db: AsyncSession) -> Sequence[SysDoc]:
        """
        获取所有 SysDoc

        :param db:
        :return:
        """
        return await self.select_models(db)
    
    from sqlalchemy.future import select


    async def get_column_data(self, db: AsyncSession, column: str):
        """
        获取指定列的所有数据

        :param db: AsyncSession
        :param column: 列名
        :return: 列的所有数据
        """
        stmt = select(getattr(SysDoc, column))  # 动态获取列名
        result = await db.execute(stmt)
        return result.scalars().all()  # 获取所有列数据并返回


    async def create(self, db: AsyncSession, obj_in: CreateSysDocParam) -> SysDoc:
        """
        创建 SysDoc

        :param db:
        :param obj_in:
        :return:
        """
        dict_obj = obj_in.model_dump(exclude={'tags'})
        doc = self.model(**dict_obj)
        db.add(doc)
        return doc

    async def update(self, db: AsyncSession, pk: int, obj_in: UpdateSysDocParam) -> int:
        """
        更新 SysDoc

        :param db:
        :param pk:
        :param obj_in:
        :return:
        """
        dict_obj = obj_in.model_dump(exclude={'tags'}, exclude_unset=True)
        return await self.update_model(db, pk, dict_obj)
    

    async def base_update(self, db: AsyncSession, pk: int, obj_in: dict) -> int:
        return await self.update_model(db, pk, obj_in)


    async def check_owned(self, db: AsyncSession, pk: int, owner_id: int) -> bool:
        """校验文档是否属于指定用户"""
        stmt = select(func.count(self.model.id)).where(
            self.model.id == pk, self.model.created_by == owner_id
        )
        result = await db.execute(stmt)
        return (result.scalar() or 0) > 0

    async def delete_owned(self, db: AsyncSession, pk: list[int], owner_id: int) -> int:
        """仅删除属于指定用户的文档"""
        return await self.delete_model_by_column(
            db, allow_multiple=True, id__in=pk, created_by=owner_id
        )

    async def delete(self, db: AsyncSession, pk: list[int]) -> int:
        """
        删除 SysDoc

        :param db:
        :param pk:
        :return:
        """
        return  await self.delete_model_by_column(db, allow_multiple=True, id__in=pk)


    async def get_children(self, db: AsyncSession, parent_id: int) -> Sequence[SysDoc]:
        """
        获取属于指定文档的子文件列表

        :param db:
        :param parent_id: 父文档ID
        :return:
        """
        stmt = (
            select(self.model)
            .where(self.model.belong == parent_id)
            .order_by(self.model.created_time.desc())
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_hot_docs(self, db: AsyncSession, user_id: int = None) -> Sequence[SysDoc]:
        stmt = select(self.model).order_by(self.model.created_time.desc()).limit(10)
        if user_id is not None:
            stmt = stmt.where(self.model.created_by == user_id)
        docs = await db.execute(stmt)
        return docs.scalars()


    async def get_count(self, db: AsyncSession, user_id: int | None = None):
        """
        获取文档统计数量

        :param db: 数据库会话
        :param user_id: 用户ID，为 None 时查询所有文档（管理员）
        :return: 包含总数和按类型分组的字典
        """
        # 构建基础条件
        where_conditions = []
        if user_id is not None:
            where_conditions.append(self.model.created_by == user_id)

        # 查询总数
        count_query = select(func.count(self.model.id))
        if where_conditions:
            count_query = count_query.where(*where_conditions)
        result = await db.execute(count_query)
        all_count = result.scalars().first()

        # 按类型分组统计
        group_query = select(
            self.model.type,
            func.count(self.model.id)
        )
        if where_conditions:
            group_query = group_query.where(*where_conditions)
        group_query = group_query.group_by(self.model.type)

        result = await db.execute(group_query)
        group = {row[0]: row[1] for row in result.fetchall()}

        return {
            'all': all_count,
            'group': group,
        }

sys_doc_dao: CRUDSysDoc = CRUDSysDoc(SysDoc)
