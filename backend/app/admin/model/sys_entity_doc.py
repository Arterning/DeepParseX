#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy import BIGINT, Column, ForeignKey, Integer, Table

from backend.common.model import MappedBase

sys_entity_doc = Table(
    'sys_entity_doc',
    MappedBase.metadata,
    Column('id', BIGINT, primary_key=True, unique=True, index=True, autoincrement=True, comment='主键ID'),
    Column('entity_id', BIGINT, ForeignKey('sys_entity.id', ondelete='CASCADE'), primary_key=True, comment='实体ID'),
    Column('doc_id', BIGINT, ForeignKey('sys_doc.id', ondelete='CASCADE'), primary_key=True, comment='文档ID'),
)