#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy.dialects.postgresql import TEXT, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from backend.common.model import Base, id_key, UserMixin


class Text2SQLTable(Base, UserMixin):
    """Text-to-SQL 白名单表元数据"""

    __tablename__ = 'sys_text2sql_table'

    id: Mapped[id_key] = mapped_column(init=False)
    schema_name: Mapped[str] = mapped_column(TEXT, default='public', comment='Schema名称')
    table_name: Mapped[str | None] = mapped_column(TEXT, default=None, comment='表名')
    display_name: Mapped[str | None] = mapped_column(TEXT, default=None, comment='中文展示名称')
    description: Mapped[str | None] = mapped_column(TEXT, default=None, comment='中文业务描述，用于向量检索')
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024), default=None, comment='description的1024维向量')
    is_active: Mapped[bool] = mapped_column(default=True, comment='是否启用（在白名单中）')

    columns: Mapped[list['Text2SQLColumn']] = relationship(
        'Text2SQLColumn',
        back_populates='table',
        cascade='all, delete-orphan',
        init=False,
    )

    @property
    def has_embedding(self) -> bool:
        return self.embedding is not None
