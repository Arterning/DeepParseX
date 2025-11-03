#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Union
from sqlalchemy import String, ForeignKey, text
from sqlalchemy.schema import Index
from sqlalchemy.dialects.postgresql import TEXT, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from backend.common.model import Base, id_key


class SysDocEmbedding(Base):
    """分块向量"""

    __tablename__ = 'sys_doc_embedding'

    __table_args__ = (
        Index('ix_sys_doc_embedding', 'embedding', postgresql_using='ivfflat'),
        Index('ix_sys_doc_embedding_384', 'embedding_384', postgresql_using='ivfflat'),
        Index('ix_sys_doc_embedding_768', 'embedding_768', postgresql_using='ivfflat'),
        Index('ix_sys_doc_embedding_1536', 'embedding_1536', postgresql_using='ivfflat'),
    )

    id: Mapped[id_key] = mapped_column(init=False)
    chunk_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        unique=True,
        nullable=False,
        server_default=text("gen_random_uuid()::text"),
        comment='分片唯一标识',
        init=False
    )
    doc_id: Mapped[int | None] = mapped_column(
        ForeignKey('sys_doc.id', ondelete='CASCADE'), default=None, index=True, comment='文件ID'
    )
    doc_name: Mapped[str] = mapped_column(TEXT, default='', comment='文件名称', nullable=True)

    doc: Mapped[Union['SysDoc', None]] = relationship(init=False, back_populates='doc_desc')

    chunk_text: Mapped[str | None] = mapped_column(TEXT, default=None, comment='分文本')

    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024), default=None, comment='1024维向量')
    embedding_384: Mapped[list[float] | None] = mapped_column(Vector(384), default=None, comment='384维向量')
    embedding_768: Mapped[list[float] | None] = mapped_column(Vector(768), default=None, comment='768维向量')
    embedding_1536: Mapped[list[float] | None] = mapped_column(Vector(1536), default=None, comment='1536维向量')
    embedding_3072: Mapped[list[float] | None] = mapped_column(Vector(3072), default=None, comment='3072维向量')
