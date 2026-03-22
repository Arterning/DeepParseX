#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy import String, ForeignKey, BIGINT, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import TEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.common.model import Base, id_key, UserMixin


class IocRecord(Base, UserMixin):
    """IOC（失陷指标）记录"""

    __tablename__ = 'sys_ioc'

    id: Mapped[id_key] = mapped_column(init=False)

    # IOC 核心字段（kw_only=True 避免 dataclass 字段顺序冲突）
    ioc_type: Mapped[str] = mapped_column(
        String(50), comment='IOC类型: ip/domain/url/md5/sha1/sha256/email/cve', kw_only=True
    )
    value: Mapped[str] = mapped_column(TEXT, comment='IOC值（统一小写存储）', kw_only=True)

    # 可选字段
    doc_id: Mapped[int | None] = mapped_column(
        BIGINT, ForeignKey('sys_doc.id', ondelete='SET NULL'), default=None, index=True, comment='来源文档ID'
    )
    context: Mapped[str | None] = mapped_column(TEXT, default=None, comment='提取上下文（前后各100字）')
    is_defanged: Mapped[bool] = mapped_column(default=False, comment='原文是否为去牙格式，如 1.1.1[.]1')

    # 状态与关联
    status: Mapped[int] = mapped_column(
        default=0, comment='状态: 0=待确认 1=有效 2=误报'
    )
    entity_id: Mapped[int | None] = mapped_column(
        BIGINT, ForeignKey('sys_entity.id', ondelete='SET NULL'), default=None, index=True, comment='已提升为实体的ID'
    )

    # 关联
    doc: Mapped['SysDoc'] = relationship('SysDoc', init=False, lazy='noload')
    entity: Mapped['Entity'] = relationship('Entity', init=False, lazy='noload')

    __table_args__ = (
        # 同一文档内相同类型+值不重复
        UniqueConstraint('doc_id', 'ioc_type', 'value', name='uq_ioc_doc_type_value'),
        Index('ix_ioc_type_value', 'ioc_type', 'value'),
    )
