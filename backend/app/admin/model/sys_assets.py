#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy import Boolean, JSON, String
from sqlalchemy.schema import Index
from sqlalchemy.dialects.postgresql import TEXT, TSVECTOR

from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.common.model import Base, id_key


class SysAssets(Base):
    """资产"""

    __tablename__ = 'sys_assets'
    id: Mapped[id_key] = mapped_column(init=False)
    ip_addr: Mapped[str | None] = mapped_column(TEXT,default=None, comment='ip地址')
    assets_name:Mapped[str | None] = mapped_column(TEXT,default=None, comment='资产名')
    assets_ports:Mapped[list[str] | None] = mapped_column(JSON,default=None, comment='资产开放端口')
    assets_services:Mapped[list[str] | None] = mapped_column(JSON,default=None, comment='资产开放服务')
    assets_desc:Mapped[str | None] = mapped_column(TEXT,default=None, comment='资产描述')
    assets_status:Mapped[bool | None] = mapped_column(Boolean,default=None, comment='资产状态')
    assets_remarks:Mapped[str | None] = mapped_column(TEXT,default=None, comment='资产备注')