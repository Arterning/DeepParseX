#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import TEXT

from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.common.model import Base, id_key, UserMixin
from backend.app.admin.model.sys_star_doc import sys_star_doc
from backend.app.admin.model.sys_star_entity import sys_star_entity


class StarCollect(Base, UserMixin):
    """收藏夹"""

    __tablename__ = 'sys_star_collect'

    id: Mapped[id_key] = mapped_column(init=False)

    name: Mapped[str] = mapped_column(sa.String(), default='', comment='收藏夹名称')

    description: Mapped[str | None] = mapped_column(
        TEXT, default=None, comment='收藏夹描述'
    )

    docs: Mapped[list['SysDoc']] = relationship(
        init=False, secondary=sys_star_doc
    )

    entities: Mapped[list['Entity']] = relationship(
        init=False, secondary=sys_star_entity
    )
    