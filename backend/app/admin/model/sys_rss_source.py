#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import TEXT

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class RssSource(Base):
    """RSS订阅源"""

    __tablename__ = 'sys_rss_source'

    id: Mapped[id_key] = mapped_column(init=False)
    name: Mapped[str] = mapped_column(String(255), comment='订阅源名称')
    url: Mapped[str] = mapped_column(TEXT, comment='RSS订阅地址')
    category: Mapped[str | None] = mapped_column(String(100), default=None, comment='分类(tech/finance/world/china等)')
    language: Mapped[str | None] = mapped_column(String(20), default='zh', comment='语言(zh/en)')
    description: Mapped[str | None] = mapped_column(TEXT, default=None, comment='订阅源描述')
    is_active: Mapped[bool] = mapped_column(default=True, comment='是否启用')
    fetch_interval: Mapped[int] = mapped_column(default=60, comment='抓取间隔(分钟)')
    last_fetch_time: Mapped[str | None] = mapped_column(String(50), default=None, comment='最后抓取时间')
    error_count: Mapped[int] = mapped_column(default=0, comment='连续错误次数')
    priority: Mapped[int] = mapped_column(default=0, comment='优先级(数字越大越优先)')
