#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy import Integer, String
from sqlalchemy.schema import Index
from sqlalchemy.dialects.postgresql import TEXT, TSVECTOR

from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.common.model import Base, id_key


class SysOrg(Base):
    """组织"""

    __tablename__ = 'sys_org'
    id: Mapped[id_key] = mapped_column(init=False)
    org_name: Mapped[str | None] = mapped_column(TEXT,default=None, comment='组织名称')
    org_file_nums: Mapped[int | None] = mapped_column(Integer,default=None, comment='组织文件数量')
    org_assets_nums: Mapped[int | None] = mapped_column(Integer,default=None, comment='组织资产数量')
    org_desc: Mapped[str | None] = mapped_column(TEXT,default=None, comment='组织描述')