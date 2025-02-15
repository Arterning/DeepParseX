#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import TEXT

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class Person(Base):
    """人物"""

    __tablename__ = 'sys_person'

    id: Mapped[id_key] = mapped_column(init=False)
    
    name: Mapped[str] = mapped_column(sa.String(), default='', comment='人物名称')
    