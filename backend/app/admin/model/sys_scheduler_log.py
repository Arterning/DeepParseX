#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import TIMESTAMP

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class SysSchedulerLog(Base):
    """定时任务执行日志"""

    __tablename__ = 'sys_scheduler_log'

    id: Mapped[id_key] = mapped_column(init=False)
    job_id: Mapped[str] = mapped_column(String(100), comment='任务ID')
    job_name: Mapped[str] = mapped_column(String(200), comment='任务名称')
    started_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), comment='开始时间')
    finished_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), default=None, comment='结束时间')
    duration_ms: Mapped[int | None] = mapped_column(default=None, comment='耗时(毫秒)')
    processed: Mapped[int] = mapped_column(default=0, comment='处理数量')
    success: Mapped[int] = mapped_column(default=0, comment='成功数量')
    error: Mapped[int] = mapped_column(default=0, comment='失败数量')
    status: Mapped[str] = mapped_column(String(20), default='running', comment='状态(running/success/partial_error/failed)')
