#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Union
from sqlalchemy import String, ForeignKey
from sqlalchemy.schema import Index
from sqlalchemy.dialects.postgresql import TEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from backend.common.model import Base, id_key


class SysDocChunk(Base):
    """分块向量"""

    __tablename__ = 'sys_doc_chunk'

    __table_args__ = (
        Index('ix_sys_doc_chunk_embedding', 'chunk_embedding', postgresql_using='ivfflat'),
    )

    id: Mapped[id_key] = mapped_column(init=False)
    doc_id: Mapped[int | None] = mapped_column(
        ForeignKey('sys_doc.id', ondelete='CASCADE'), default=None, index=True, comment='文件ID'
    )
    doc_name: Mapped[str] = mapped_column(TEXT, default='', comment='文件名称', nullable=True)

    doc: Mapped[Union['SysDoc', None]] = relationship(init=False, back_populates='doc_chunk')

    chunk_text: Mapped[str | None] = mapped_column(TEXT, default=None, comment='chunk 文本')

    chunk_embedding: Mapped[list[float] | None] = mapped_column(Vector(1024), default=None, comment='chunk 向量')
