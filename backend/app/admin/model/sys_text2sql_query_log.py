#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy.dialects.postgresql import TEXT
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key, UserMixin


class Text2SQLQueryLog(Base, UserMixin):
    """Text-to-SQL 查询日志"""

    __tablename__ = 'sys_text2sql_query_log'

    id: Mapped[id_key] = mapped_column(init=False)
    question: Mapped[str | None] = mapped_column(TEXT, default=None, comment='用户原始问题')
    generated_sql: Mapped[str | None] = mapped_column(TEXT, default=None, comment='最终生成的SQL')
    status: Mapped[str] = mapped_column(
        TEXT, default='success', comment='执行状态：success/error/timeout/clarification'
    )
    error_message: Mapped[str | None] = mapped_column(TEXT, default=None, comment='错误信息')
    row_count: Mapped[int | None] = mapped_column(default=None, comment='返回行数')
    execution_time_ms: Mapped[int | None] = mapped_column(default=None, comment='执行耗时（毫秒）')
    retry_count: Mapped[int] = mapped_column(default=0, comment='self-correction重试次数')
    feedback: Mapped[int | None] = mapped_column(default=None, comment='用户反馈：1=好评，0=差评，null=未评价')
    feedback_sql: Mapped[str | None] = mapped_column(TEXT, default=None, comment='用户提供的正确SQL')
