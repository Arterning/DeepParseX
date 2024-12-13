#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.schema import Index
from sqlalchemy.dialects.postgresql import TEXT, TSVECTOR

from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.common.model import Base, id_key


class SysOrgDoc(Base):
    """组织文件表"""

    __tablename__ = 'sys_org_doc'
    
    id: Mapped[id_key] = mapped_column(init=False)
    org_id: Mapped[int | None] = mapped_column(
        ForeignKey('sys_org.id', ondelete='CASCADE'), default=None, index=True, comment='组织id'
    )
    doc_id: Mapped[int | None] = mapped_column(
        ForeignKey('sys_doc.id', ondelete='CASCADE'), default=None, index=True, comment='文件id'
    )
