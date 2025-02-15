#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import TEXT

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class News(Base):
    """新闻"""

    __tablename__ = 'sys_news'

    id: Mapped[id_key] = mapped_column(init=False)
    
    name: Mapped[str] = mapped_column(sa.String(), default='', comment='新闻标题')
    