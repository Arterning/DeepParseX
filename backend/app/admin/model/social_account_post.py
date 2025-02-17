#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Union
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import TEXT

from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.common.model import Base, id_key


# 简介：贴文的简介信息。
# 原文：贴文的原文内容。
# 内容：贴文的翻译内容。
# 时间：贴文的发表时间。

class SocialAccountPost(Base):
    """社交帖子"""

    __tablename__ = 'social_account_post'

    id: Mapped[id_key] = mapped_column(init=False)
    
    name: Mapped[str] = mapped_column(sa.String(500), default='', comment='名称')
    original: Mapped[str] = mapped_column(TEXT, default='', comment='原文')
    content: Mapped[str] = mapped_column(TEXT, default='', comment='翻译')
    time: Mapped[datetime | None] = mapped_column(default=None, comment='时间')

    social_account_id: Mapped[int | None] = mapped_column(
        ForeignKey('social_account.id', ondelete='SET NULL'), default=None, comment='社交账户ID'
    )
    social_account: Mapped[Union['SocialAccount', None]] = relationship(init=False, back_populates='posts')
    