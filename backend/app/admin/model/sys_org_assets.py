#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy import INT, Column, ForeignKey, Integer, Table

from backend.common.model import MappedBase

sys_org_assets = Table(
    'sys_org_assets',
    MappedBase.metadata,
    Column('id', INT, primary_key=True, unique=True, index=True, autoincrement=True, comment='主键ID'),
    Column('org_id', Integer, ForeignKey('sys_org.id', ondelete='CASCADE'), primary_key=True, comment='组织ID'),
    Column('asset_id', Integer, ForeignKey('sys_assets.id', ondelete='CASCADE'), primary_key=True, comment='资产ID'),
)
