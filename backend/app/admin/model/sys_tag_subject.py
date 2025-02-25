
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy import BIGINT, Column, ForeignKey, Integer, Table

from backend.common.model import MappedBase

sys_tag_subject = Table(
    'sys_tag_subject',
    MappedBase.metadata,
    Column('id', BIGINT, primary_key=True, unique=True, index=True, autoincrement=True, comment='主键ID'),
    Column('tag_id', BIGINT, ForeignKey('sys_tag.id', ondelete='CASCADE'), primary_key=True, comment='标签ID'),
    Column('subject_id', BIGINT, ForeignKey('sys_subject.id', ondelete='CASCADE'), primary_key=True, comment='议题ID'),
)
