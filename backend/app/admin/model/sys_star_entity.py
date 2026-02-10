#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy import BIGINT, Column, ForeignKey, Table

from backend.common.model import MappedBase

sys_star_entity = Table(
    'sys_star_entity',
    MappedBase.metadata,
    Column('id', BIGINT, primary_key=True, unique=True, index=True, autoincrement=True, comment='主键ID'),
    Column('star_id', BIGINT, ForeignKey('sys_star_collect.id', ondelete='CASCADE'), primary_key=True, comment='收藏夹ID'),
    Column('entity_id', BIGINT, ForeignKey('sys_entity.id', ondelete='CASCADE'), primary_key=True, comment='实体ID'),
    Column('created_by', BIGINT, comment='创建人ID'),
)
