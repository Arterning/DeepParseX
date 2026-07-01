#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
from sqlalchemy import UUID, String, ForeignKey
from sqlalchemy.schema import Index
from sqlalchemy.dialects.postgresql import TEXT, JSONB

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import TIMESTAMP
from backend.utils.timezone import timezone
from backend.common.model import Base, id_key
from backend.app.admin.model.sys_tag_doc import sys_tag_doc
from backend.app.admin.model.sys_entity_doc import sys_entity_doc

class SysDoc(Base):
    """文件"""

    __tablename__ = 'sys_doc'

    __table_args__ = (
        Index('ix_sys_document_created_time', 'created_time'),
        Index('ix_sys_document_updated_time', 'updated_time'),
    )

    id: Mapped[id_key] = mapped_column(init=False)
    title: Mapped[str] = mapped_column(TEXT, default='', comment='文件原名')
    name: Mapped[str] = mapped_column(TEXT, default='', comment='文件名称（翻译后）')
    type: Mapped[str] = mapped_column(String(500), default=None, comment='类型')
    file_suffix: Mapped[str | None] = mapped_column(String(500), default=None, comment='文件后缀')
    content: Mapped[str | None] = mapped_column(TEXT, default=None, comment='文件内容（文本，用于分词索引）')
    workbook: Mapped[str | None] = mapped_column(TEXT, default=None, comment='Workbook JSON（表格编辑器专用）')
    desc: Mapped[str | None] = mapped_column(TEXT, default=None, comment='摘要')
    translation: Mapped[str | None] = mapped_column(TEXT, default=None, comment='翻译内容')
    file: Mapped[str | None] = mapped_column(TEXT, default=None, comment='文件原件')
    error_msg: Mapped[str | None] = mapped_column(TEXT, default=None, comment='错误信息')
    source: Mapped[str | None] = mapped_column(TEXT, default=None, comment='文件来源')
    belong: Mapped[int | None] = mapped_column(default=None, comment='文件属于')
    uuid: Mapped[UUID] = mapped_column(UUID(as_uuid=True), default=None,nullable=True, unique=True, comment='唯一标识符')
    
    doc_time: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), default=None, init=True, sort_order=99, comment='文件创建时间'
    )
    size: Mapped[int | None] = mapped_column(default=None, comment='文件大小')
    status: Mapped[int | None] = mapped_column(default=1, comment='文件状态(0解析中 1正常 2出错)')
    process_status: Mapped[dict | None] = mapped_column(JSONB, default=None, comment='处理进度状态')
    entity_extracted: Mapped[int | None] = mapped_column(default=0, comment='是否已提取实体(0未提取 1已提取)')
    graph_extracted: Mapped[int | None] = mapped_column(default=0, comment='是否已构建知识图谱(0未构建 1已构建)')
    language: Mapped[str | None] = mapped_column(String(50), default=None, comment='文件语言')
    ocr_pages: Mapped[list[dict] | None] = mapped_column(JSONB, default=None, comment='OCR分页原始结果')
    ocr_pages_translation: Mapped[list[dict] | None] = mapped_column(JSONB, default=None, comment='OCR分页翻译结果')
    refined_markdown: Mapped[str | None] = mapped_column(TEXT, default=None, comment='AI精炼的结构化Markdown内容（含章节、标题、关键词、摘要，原文与翻译分样式展示）')
    translate_image: Mapped[str | None] = mapped_column(TEXT, default=None, comment='翻译后图片路径(MinIO)')

    dept_id: Mapped[int | None] = mapped_column(
        ForeignKey('sys_dept.id', ondelete='SET NULL'), default=None, comment='部门关联ID'
    )
    doc_dir_id: Mapped[int | None] = mapped_column(
        ForeignKey('sys_doc_dir.id', ondelete='SET NULL'), default=None, comment='目录关联ID'
    )
    
    upload_task_id: Mapped[int | None] = mapped_column(
        ForeignKey('sys_upload_task.id', ondelete='SET NULL'), default=None, comment='上传任务ID'
    )
    created_by: Mapped[int | None] = mapped_column(default=None, comment='创建人ID')
    created_user: Mapped[str | None] = mapped_column(TEXT, default=None, comment='创建人')
    updated_by: Mapped[int | None] = mapped_column(init=False, default=None, comment='修改人ID')
    updated_user: Mapped[str | None] = mapped_column(TEXT, default=None, comment='修改人')

    doc_dir: Mapped['SysDocDir'] = relationship(init=False, back_populates='docs')
    email_msg: Mapped['MailMsg'] = relationship(init=False, back_populates='doc')
    doc_data: Mapped[list['SysDocData']] = relationship(init=False, back_populates='doc')
    doc_chunks: Mapped[list['SysDocChunk']] = relationship(init=False, back_populates='doc')
    doc_desc: Mapped[list['SysDocEmbedding']] = relationship(init=False, back_populates='doc')
    doc_spos: Mapped[list['SubjectPredictObject']] = relationship(init=False, back_populates='doc')

    tags: Mapped[list['Tag']] = relationship(
        init=False, secondary=sys_tag_doc, back_populates='docs'
    )

    entities: Mapped[list['Entity']] = relationship(
        init=False, secondary=sys_entity_doc, back_populates='docs'
    )