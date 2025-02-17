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


# 简介：邮件的简介信息。
# 原文：邮件的原文内容。
# 内容：邮件的翻译内容。
# 内容分类：邮件内容的分类，如工作邮件、广告邮件等。
# 发送者：内容的发送邮箱。
# 接收者：内容的接收邮箱。
# 抄送者：抄送邮箱。
# 时间：邮件发送时间。
# 附件：附件的文件路径，点击后跳转至该文件的内容。

class MailMsg(Base):
    """邮件"""

    __tablename__ = 'mail_msg'

    id: Mapped[id_key] = mapped_column(init=False)
    
    name: Mapped[str] = mapped_column(sa.String(500), default='', comment='邮件标题')
    
    original: Mapped[str] = mapped_column(TEXT, default='', comment='原文')
    
    content: Mapped[str] = mapped_column(TEXT, default='', comment='翻译')
    
    time: Mapped[datetime | None] = mapped_column(default=None, comment='时间')

    # 分类
    category: Mapped[str] = mapped_column(sa.String(500), default='', comment='分类')

    # 发送者
    sender: Mapped[str] = mapped_column(sa.String(500), default='', comment='发送者邮箱')

    # 接收者
    receiver: Mapped[str] = mapped_column(sa.String(500), default='', comment='接收者邮箱')

    # 抄送者
    cc: Mapped[str] = mapped_column(TEXT, default='', comment='抄送者')

    # 附件
    attachments: Mapped[list['MailAttachment']] = relationship(init=False, back_populates='mail_msg')
    