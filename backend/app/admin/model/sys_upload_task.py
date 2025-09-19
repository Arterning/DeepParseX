#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import TEXT, JSON

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class UploadTask(Base):
    """上传任务"""

    __tablename__ = 'sys_upload_task'

    id: Mapped[id_key] = mapped_column(init=False)
    
    name: Mapped[str | None] = mapped_column(sa.String(), default='', comment='任务名称')
    
    status: Mapped[str | None] = mapped_column(sa.String(), default='', comment='任务状态')

    option: Mapped[JSON | None] = mapped_column(JSON, default=None, comment='任务选项')
    