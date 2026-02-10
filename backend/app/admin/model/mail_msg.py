#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Union
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import TEXT, JSON

from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.common.model import Base, id_key, UserMixin



class MailMsg(Base, UserMixin):
    """邮件"""

    __tablename__ = 'mail_msg'

    id: Mapped[id_key] = mapped_column(init=False)
    
    name: Mapped[str] = mapped_column(TEXT, default='', comment='邮件标题')

    subject: Mapped[str | None] = mapped_column(TEXT, default='', comment='邮件主题')
    
    original: Mapped[str] = mapped_column(TEXT, default='', comment='原文')

    zh_subject: Mapped[str | None] = mapped_column(TEXT, default='', comment='翻译主题')
    
    zh_content: Mapped[str | None] = mapped_column(TEXT, default='', comment='翻译')
    
    time: Mapped[datetime | None] = mapped_column(default=None, comment='时间')

    # 分类
    category: Mapped[str | None] = mapped_column(TEXT, default='', comment='分类')

    # 发送者
    sender: Mapped[str] = mapped_column(TEXT, default='', comment='发送者邮箱')

    from_row: Mapped[str | None] = mapped_column(TEXT, default='', comment='发送者')

    # 接收者
    receiver: Mapped[str] = mapped_column(TEXT, default='', comment='接收者邮箱')

    to_row: Mapped[str | None] = mapped_column(TEXT, default='', comment='接收者')

    # 抄送者
    cc: Mapped[str | None] = mapped_column(TEXT, default='', comment='抄送者')

    cc_row: Mapped[str | None] = mapped_column(TEXT, default='', comment='抄送者')

    # 密送者
    bcc: Mapped[str | None] = mapped_column(TEXT, default='', comment='密送者')

    bcc_row: Mapped[str | None] = mapped_column(TEXT, default='', comment='密送者')

    # 附件
    attachments: Mapped[JSON | None] = mapped_column(JSON, default=None, comment='附件')

    doc_id: Mapped[int | None] = mapped_column(
        ForeignKey('sys_doc.id', ondelete='CASCADE'), default=None, index=True, comment='文件ID'
    )

    doc_dir_id: Mapped[int | None] = mapped_column(
        ForeignKey('sys_doc_dir.id', ondelete='SET NULL'), default=None, index=True, comment='目录ID'
    )

    doc: Mapped[Union['SysDoc', None]] = relationship(init=False, back_populates='email_msg')

    doc_name: Mapped[str | None] = mapped_column(TEXT, default='', comment='文件名称')

    detection_result: Mapped[int] = mapped_column(default=0, comment='检测结果：0=正常邮件，1=垃圾邮件，2=疑似垃圾邮件')
    