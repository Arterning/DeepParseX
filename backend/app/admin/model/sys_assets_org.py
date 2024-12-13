#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.schema import Index
from sqlalchemy.dialects.postgresql import TEXT, TSVECTOR

from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.common.model import Base, id_key


class SysAssetsOrg(Base):
    """组织文件表"""

    __tablename__ = 'sys_assets_org'
    
    id: Mapped[id_key] = mapped_column(init=False)

    assets_id: Mapped[int | None] = mapped_column(
        ForeignKey('sys_assets.id', ondelete='CASCADE'), default=None, index=True, comment='资产id'
    )
    org_id: Mapped[int | None] = mapped_column(
        ForeignKey('sys_org.id', ondelete='CASCADE'), default=None, index=True, comment='组织id'
    )
