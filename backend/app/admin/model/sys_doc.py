#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
from sqlalchemy import UUID, String, ForeignKey
from sqlalchemy.schema import Index
from sqlalchemy.dialects.postgresql import TEXT, TSVECTOR

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import TIMESTAMP
from backend.utils.timezone import timezone
from backend.common.model import Base, id_key


class SysDoc(Base):
    """文件"""

    __tablename__ = 'sys_doc'

    __table_args__ = (
        Index('ix_sys_document_created_time', 'created_time'),
        Index('ix_sys_document_updated_time', 'updated_time'),
    )

    id: Mapped[id_key] = mapped_column(init=False)
    title: Mapped[str] = mapped_column(TEXT, default='', comment='文件原名')
    name: Mapped[str] = mapped_column(TEXT, default='', comment='文件主题')
    type: Mapped[str] = mapped_column(String(500), default=None, comment='类型')
    file_suffix: Mapped[str | None] = mapped_column(String(500), default=None, comment='文件后缀')
    content: Mapped[str | None] = mapped_column(TEXT, default=None, comment='文件内容')
    desc: Mapped[str | None] = mapped_column(TEXT, default=None, comment='摘要')
    file: Mapped[str | None] = mapped_column(TEXT, default=None, comment='原文')
    doc_tokens: Mapped[str | None] = mapped_column(TEXT, default=None, comment='分词内容')
    doc_vector: Mapped[TSVECTOR | None] = mapped_column(TSVECTOR, default=None, comment='分词向量')
    error_msg: Mapped[str | None] = mapped_column(TEXT, default=None, comment='错误信息')
    source: Mapped[str | None] = mapped_column(TEXT, default=None, comment='文件来源')
    belong: Mapped[int | None] = mapped_column(default=None, comment='文件属于')
    uuid: Mapped[UUID] = mapped_column(UUID(as_uuid=True), default=None,nullable=True, unique=True, comment='唯一标识符')
    
    doc_time: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), default=None, init=True, sort_order=99, comment='文件创建时间'
    )
    size: Mapped[int | None] = mapped_column(default=None, comment='文件大小')
    status: Mapped[int | None] = mapped_column(default=1, comment='文件状态(0解析中 1正常 2出错)')

    dept_id: Mapped[int | None] = mapped_column(
        ForeignKey('sys_dept.id', ondelete='SET NULL'), default=None, comment='部门关联ID'
    )
    created_by: Mapped[int | None] = mapped_column(default=None, comment='创建人ID')
    created_user: Mapped[str | None] = mapped_column(TEXT, default=None, comment='创建人')
    updated_by: Mapped[int | None] = mapped_column(init=False, default=None, comment='修改人ID')
    updated_user: Mapped[str | None] = mapped_column(TEXT, default=None, comment='修改人')

    doc_data: Mapped[list['SysDocData']] = relationship(init=False, back_populates='doc')
    doc_chunk: Mapped[list['SysDocChunk']] = relationship(init=False, back_populates='doc')
    doc_desc: Mapped[list['SysDocEmbedding']] = relationship(init=False, back_populates='doc')
    doc_spos: Mapped[list['SubjectPredictObject']] = relationship(init=False, back_populates='doc')