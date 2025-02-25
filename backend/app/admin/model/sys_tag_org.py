
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy import BIGINT, Column, ForeignKey, Integer, Table

from backend.common.model import MappedBase

sys_tag_org = Table(
    'sys_tag_org',
    MappedBase.metadata,
    Column('id', BIGINT, primary_key=True, unique=True, index=True, autoincrement=True, comment='主键ID'),
    Column('tag_id', BIGINT, ForeignKey('sys_tag.id', ondelete='CASCADE'), primary_key=True, comment='标签ID'),
    Column('org_id', BIGINT, ForeignKey('sys_org.id', ondelete='CASCADE'), primary_key=True, comment='机构ID'),
)