#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Union
from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import TEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.common.model import Base, id_key


class Scandal(Base):
    """黑料"""

    __tablename__ = 'sys_scandal'

    id: Mapped[id_key] = mapped_column(init=False)
    name: Mapped[str | None] = mapped_column(String(255), default=None, comment='名称')
    content: Mapped[str | None] = mapped_column(TEXT, default=None, comment='黑料内容')