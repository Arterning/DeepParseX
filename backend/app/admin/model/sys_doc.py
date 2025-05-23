#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy import UUID, String
from sqlalchemy.schema import Index
from sqlalchemy.dialects.postgresql import TEXT, TSVECTOR

from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.common.model import Base, id_key


class SysDoc(Base):
    """文件"""

    __tablename__ = 'sys_doc'

    __table_args__ = (
        Index('ix_sys_document_created_time', 'created_time'),
        Index('ix_sys_document_updated_time', 'updated_time'),
    )

    id: Mapped[id_key] = mapped_column(init=False)
    title: Mapped[str] = mapped_column(TEXT, default='', comment='标题')
    name: Mapped[str] = mapped_column(TEXT, default='', comment='名称')
    type: Mapped[str] = mapped_column(String(500), default=None, comment='类型')
    file_suffix: Mapped[str | None] = mapped_column(String(500), default=None, comment='文件后缀')
    content: Mapped[str | None] = mapped_column(TEXT, default=None, comment='文件内容')
    desc: Mapped[str | None] = mapped_column(TEXT, default=None, comment='摘要')
    file: Mapped[str | None] = mapped_column(TEXT, default=None, comment='原文')
    c_tokens: Mapped[str | None] = mapped_column(TEXT, default=None, comment='分词内容')
    tokens: Mapped[TSVECTOR | None] = mapped_column(TSVECTOR, default=None, comment='分词向量')
    belong: Mapped[int | None] = mapped_column(default=None, comment='文件属于')
    account_pwd: Mapped[str|None] = mapped_column(TEXT,default=None,comment="用户名密码")
    uuid: Mapped[UUID] = mapped_column(UUID(as_uuid=True), default=None,nullable=True, unique=True, comment='唯一标识符')
    
    doc_data: Mapped[list['SysDocData']] = relationship(init=False, back_populates='doc')
    doc_chunk: Mapped[list['SysDocChunk']] = relationship(init=False, back_populates='doc')
    doc_desc: Mapped[list['SysDocEmbedding']] = relationship(init=False, back_populates='doc')
    doc_spos: Mapped[list['SubjectPredictObject']] = relationship(init=False, back_populates='doc')