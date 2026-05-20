#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy import ForeignKey, BIGINT
from sqlalchemy.dialects.postgresql import TEXT, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.common.model import Base, id_key


class Text2SQLColumn(Base):
    """Text-to-SQL 字段元数据"""

    __tablename__ = 'sys_text2sql_column'

    id: Mapped[id_key] = mapped_column(init=False)
    table_id: Mapped[int | None] = mapped_column(
        BIGINT, ForeignKey('sys_text2sql_table.id', ondelete='CASCADE'), default=None, comment='所属表ID'
    )
    column_name: Mapped[str | None] = mapped_column(TEXT, default=None, comment='字段名')
    data_type: Mapped[str | None] = mapped_column(TEXT, default=None, comment='数据类型')
    description: Mapped[str | None] = mapped_column(TEXT, default=None, comment='中文字段说明')
    sample_values: Mapped[list | None] = mapped_column(JSON, default=None, comment='样例值，辅助LLM理解枚举值')
    is_sensitive: Mapped[bool] = mapped_column(default=False, comment='是否为敏感字段')
    ordinal_position: Mapped[int | None] = mapped_column(default=None, comment='字段在表中的顺序位置')

    table: Mapped['Text2SQLTable'] = relationship(
        'Text2SQLTable', back_populates='columns', init=False
    )
