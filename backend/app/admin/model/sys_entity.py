#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Union, Dict, Any, List
from sqlalchemy import String, ForeignKey, BIGINT
from sqlalchemy.dialects.postgresql import TEXT, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.common.model import Base, id_key, UserMixin
from backend.app.admin.model.sys_entity_doc import sys_entity_doc


class Entity(Base, UserMixin):
    """实体"""

    __tablename__ = 'sys_entity'

    id: Mapped[id_key] = mapped_column(init=False)
    name: Mapped[str | None] = mapped_column(TEXT, default=None, comment='实体名称')
    description: Mapped[str | None] = mapped_column(TEXT, default=None, comment='实体描述')
    entity_type: Mapped[str | None] = mapped_column(String(255), default=None, comment='实体类型')
    properties: Mapped[Dict[str, Any] | None] = mapped_column(JSON, default=None, comment='实体属性')
    matched_chunks: Mapped[List[Dict[str, Any]] | None] = mapped_column(JSON, default=None, comment='包含实体名称的文本片段')
    profile: Mapped[str | None] = mapped_column(TEXT, default=None, comment='实体画像（详细画像信息）')

    # 首次发现来源
    source_doc_id: Mapped[int | None] = mapped_column(BIGINT, default=None, comment='首次发现来源文档ID')
    source_doc_name: Mapped[str | None] = mapped_column(TEXT, default=None, comment='首次发现来源文档名称')

    # 关联到实体类型表
    entity_type_id: Mapped[int | None] = mapped_column(
        BIGINT, ForeignKey('sys_entity_type.id', ondelete='SET NULL'), default=None, comment='实体类型ID'
    )

    docs: Mapped[list['SysDoc']] = relationship(
        init=False, secondary=sys_entity_doc, back_populates='entities'
    )
    entity_type_rel: Mapped['EntityType'] = relationship(
        'EntityType', back_populates='entities', init=False
    )
