#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy.dialects.postgresql import TEXT
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from backend.common.model import Base, id_key, UserMixin


class Text2SQLExample(Base, UserMixin):
    """Text-to-SQL Few-shot 示例"""

    __tablename__ = 'sys_text2sql_example'

    id: Mapped[id_key] = mapped_column(init=False)
    question: Mapped[str | None] = mapped_column(TEXT, default=None, comment='自然语言问题')
    sql: Mapped[str | None] = mapped_column(TEXT, default=None, comment='对应的正确SQL')
    question_embedding: Mapped[list[float] | None] = mapped_column(
        Vector(1024), default=None, comment='问题的1024维向量，用于相似检索'
    )
    source: Mapped[str] = mapped_column(
        TEXT, default='manual', comment='来源：manual=手动添加，feedback=用户反馈转入'
    )

    @property
    def has_embedding(self) -> bool:
        return self.question_embedding is not None
