#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime

from sqlalchemy import String, Date
from sqlalchemy.dialects.postgresql import TEXT, TIMESTAMP, JSONB

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key
from backend.utils.timezone import timezone


class Briefing(Base):
    """每日简报"""

    __tablename__ = 'sys_briefing'

    id: Mapped[id_key] = mapped_column(init=False)
    title: Mapped[str] = mapped_column(String(500), comment='简报标题')
    date: Mapped[datetime] = mapped_column(Date, comment='简报日期')
    summary: Mapped[str | None] = mapped_column(TEXT, default=None, comment='简报摘要')
    content: Mapped[str | None] = mapped_column(TEXT, default=None, comment='简报正文(Markdown格式)')
    key_points: Mapped[dict | None] = mapped_column(JSONB, default=None, comment='关键要点(JSON数组)')
    categories: Mapped[dict | None] = mapped_column(JSONB, default=None, comment='分类统计(JSON对象)')
    source_count: Mapped[int] = mapped_column(default=0, comment='引用文章数量')
    doc_ids: Mapped[dict | None] = mapped_column(JSONB, default=None, comment='引用的文档ID列表')
    status: Mapped[int] = mapped_column(default=0, comment='状态(0生成中 1已完成 2失败)')
    error_msg: Mapped[str | None] = mapped_column(TEXT, default=None, comment='错误信息')
    model_used: Mapped[str | None] = mapped_column(String(100), default=None, comment='使用的AI模型')
    generation_time: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), default=None, comment='生成完成时间'
    )
