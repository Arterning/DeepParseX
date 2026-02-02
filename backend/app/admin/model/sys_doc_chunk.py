#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Union
from sqlalchemy import String, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import TEXT, TSVECTOR
from sqlalchemy.schema import Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.common.model import Base, id_key


class SysDocChunk(Base):
    """文档分块数据"""

    __tablename__ = 'sys_doc_chunk'

    __table_args__ = (
        Index('ix_sys_doc_chunk_vector', 'chunk_vector', postgresql_using='gin'),
        Index('ix_sys_doc_chunk_translation_vector', 'chunk_translation_vector', postgresql_using='gin'),
    )

    id: Mapped[id_key] = mapped_column(init=False)
    doc_id: Mapped[int | None] = mapped_column(
        ForeignKey('sys_doc.id', ondelete='CASCADE'), default=None, index=True, comment='文档ID'
    )

    chunk_index: Mapped[int] = mapped_column(Integer, default=0, comment='分块索引（从0开始）')
    chunk_text: Mapped[str | None] = mapped_column(TEXT, default=None, comment='分块文本内容')
    chunk_vector: Mapped[TSVECTOR | None] = mapped_column(TSVECTOR, default=None, comment='分块文本分词向量')

    # 翻译相关字段（暂时保留，后续实现）
    chunk_translation: Mapped[str | None] = mapped_column(TEXT, default=None, comment='分块翻译内容')
    chunk_translation_vector: Mapped[TSVECTOR | None] = mapped_column(TSVECTOR, default=None, comment='翻译分词向量')

    doc: Mapped[Union['SysDoc', None]] = relationship(init=False, back_populates='doc_chunks')
