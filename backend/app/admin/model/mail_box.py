#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Union
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import String, ForeignKey, Integer, Index
from sqlalchemy.dialects.postgresql import TEXT

from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.common.model import Base, id_key, UserMixin
from backend.app.admin.model.sys_mail_box_tag import sys_mail_box_tag


class MailBox(Base, UserMixin):
    """邮箱"""

    __tablename__ = 'mail_box'

    __table_args__ = (
        Index('ix_mail_box_name_trgm', 'name', postgresql_using='gin',
              postgresql_ops={'name': 'gin_trgm_ops'}),
    )

    id: Mapped[id_key] = mapped_column(init=False)
    
    name: Mapped[str] = mapped_column(String(500), default='', comment='邮箱账号')

    user_name: Mapped[str | None] = mapped_column(String(500), default='', comment='姓名')

    country: Mapped[str | None] = mapped_column(String(500), default='', comment='国家/地区')

    occupation: Mapped[str | None] = mapped_column(String(500), default='', comment='职业')

    organization: Mapped[str | None] = mapped_column(String(500), default='', comment='组织/公司')

    job_title: Mapped[str | None] = mapped_column(String(500), default='', comment='职位')

    labels: Mapped[str | None] = mapped_column(String(500), default='', comment='标签')

    email_num: Mapped[int] = mapped_column(Integer(), default=0, comment='邮件数量')

    other_info: Mapped[str | None] = mapped_column(TEXT, default='', comment='其它信息')

    profile: Mapped[str | None] = mapped_column(TEXT, default=None, comment='AI生成的邮箱画像')

    tags: Mapped[list['Tag']] = relationship(
        init=False, secondary=sys_mail_box_tag
    )
