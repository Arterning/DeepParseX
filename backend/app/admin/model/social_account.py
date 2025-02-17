#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import TEXT

from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.common.model import Base, id_key

# 姓名：社交用户的实名。
# 社交名：社交用户当前昵称。
# 曾用名：社交用户的曾用名称。
# 社交账号：社交平台账号ID。
# 国籍/地区：社交用户的国籍或地区。
# 性别：社交用户的性别。
# 标签：社交用户的标签。
# 政治面貌：社交用户的政治面貌。
# 贴文数量：社交用户的贴文数量。
# 其它信息：其它信息，可按照用户需求选择展示。

class SocialAccount(Base):
    """社交账户"""

    __tablename__ = 'social_account'

    id: Mapped[id_key] = mapped_column(init=False)
    
    name: Mapped[str] = mapped_column(sa.String(500), default='', comment='社交账户名称')
    
    social_name: Mapped[str] = mapped_column(sa.String(500), default='', comment='社交账户名称')
    
    social_account: Mapped[str] = mapped_column(sa.String(500), default='', comment='社交账户名称')
    
    country: Mapped[str] = mapped_column(sa.String(500), default='', comment='国家/地区')
    
    gender: Mapped[str] = mapped_column(sa.String(500), default='', comment='性别')
    
    labels: Mapped[str] = mapped_column(TEXT, default='', comment='标签')

    political: Mapped[str] = mapped_column(TEXT, default='', comment='政治面貌')
    
    other_info: Mapped[str] = mapped_column(TEXT, default='', comment='其它信息')

    posts: Mapped[list['SocialAccountPost']] = relationship(init=False, back_populates='social_account')
    