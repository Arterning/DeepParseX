#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy import String
from sqlalchemy.schema import Index
from sqlalchemy.dialects.postgresql import TEXT, TSVECTOR
from pgvector.sqlalchemy import Vector  # 使用pgvector提供的Vector类型

from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.common.model import Base, id_key


class SysDoc(Base):
    """文件"""

    __tablename__ = 'sys_doc'

    __table_args__ = (
        Index('ix_sys_document_created_time', 'created_time'),
        Index('ix_sys_document_updated_time', 'updated_time'),
        Index('ix_sys_document_embedding', 'embedding', postgresql_using='ivfflat'),
    )

    id: Mapped[id_key] = mapped_column(init=False)
    title: Mapped[str] = mapped_column(TEXT, default='', comment='标题')
    name: Mapped[str] = mapped_column(TEXT, default='', comment='名称')
    type: Mapped[str] = mapped_column(String(500), default=None, comment='类型')
    content: Mapped[str | None] = mapped_column(TEXT, default=None, comment='文件内容')
    desc: Mapped[str | None] = mapped_column(TEXT, default=None, comment='摘要')
    file: Mapped[str | None] = mapped_column(TEXT, default=None, comment='原文')
    c_tokens: Mapped[str | None] = mapped_column(TEXT, default=None, comment='分词内容')
    tokens: Mapped[TSVECTOR | None] = mapped_column(TSVECTOR, default=None, comment='分词向量')
    email_subject: Mapped[str | None] = mapped_column(TEXT, default=None, comment='邮件主题')
    email_from: Mapped[str | None] = mapped_column(String(500), default=None, comment='邮件发送人')
    email_to: Mapped[str | None] = mapped_column(String(500), default=None, comment='邮件接受人')
    email_time: Mapped[str | None] = mapped_column(String(500), default=None, comment='邮件时间')
    belong: Mapped[int | None] = mapped_column(default=None, comment='文件属于')
    text_embed: Mapped[str | None] = mapped_column(default=None, comment='文本向量')
    account_pwd: Mapped[str|None] = mapped_column(TEXT,default=None,comment="用户名密码")
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024), default=None, comment='文档向量')
    
    doc_data: Mapped[list['SysDocData']] = relationship(init=False, back_populates='doc')