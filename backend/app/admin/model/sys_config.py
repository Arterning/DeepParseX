#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import TEXT
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class Config(Base):
    """系统配置表"""

    __tablename__ = 'sys_config'

    id: Mapped[id_key] = mapped_column(init=False)
    login_title: Mapped[str] = mapped_column(String(20), default='登录', comment='登录页面标题')
    login_sub_title: Mapped[str] = mapped_column(
        String(50), default='DeepParseX', comment='登录页面子标题'
    )
    footer: Mapped[str] = mapped_column(String(50), default='DeepParseX', comment='页脚标题')
    logo: Mapped[str] = mapped_column(TEXT, default='Arco', comment='Logo')
    system_title: Mapped[str] = mapped_column(String(20), default='Arco', comment='系统标题')
    system_comment: Mapped[str] = mapped_column(
        TEXT,
        default='强大的多模态文档解析与知识管理平台',
        comment='系统描述',
    )
