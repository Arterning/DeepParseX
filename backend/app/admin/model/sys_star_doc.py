#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy import BIGINT, Column, ForeignKey, Integer, Table

from backend.common.model import MappedBase

sys_star_doc = Table(
    'sys_star_doc',
    MappedBase.metadata,
    Column('id', BIGINT, primary_key=True, unique=True, index=True, autoincrement=True, comment='主键ID'),
    Column('star_id', BIGINT, ForeignKey('sys_star_collect.id', ondelete='CASCADE'), primary_key=True, comment='收藏夹ID'),
    Column('doc_id', BIGINT, ForeignKey('sys_doc.id', ondelete='CASCADE'), primary_key=True, comment='文档ID'),
)