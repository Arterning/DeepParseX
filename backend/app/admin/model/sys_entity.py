#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Union, Dict, Any
from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import TEXT, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.common.model import Base, id_key


class Entity(Base):
    """实体"""

    __tablename__ = 'sys_entity'

    id: Mapped[id_key] = mapped_column(init=False)
    name: Mapped[str | None] = mapped_column(TEXT, default=None, comment='实体名称')
    description: Mapped[str | None] = mapped_column(TEXT, default=None, comment='实体描述')
    entity_type: Mapped[str | None] = mapped_column(String(255), default=None, comment='实体类型')
    properties: Mapped[Dict[str, Any] | None] = mapped_column(JSON, default=None, comment='实体属性')
