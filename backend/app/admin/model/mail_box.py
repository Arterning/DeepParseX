#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Union
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import TEXT

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key

# 姓名：邮箱账号的实名。
# 账号：邮箱号。
# 国籍/地区：邮箱号的国籍或地区。
# 标签：邮箱用户的标签。（邮件用户的标签为什么和邮箱的标签一样）
# 邮件箱数量：邮箱用户邮件数量。
# 其它信息：其它信息，可按照用户需求选择展示。

class MailBox(Base):
    """邮箱"""

    __tablename__ = 'mail_box'

    id: Mapped[id_key] = mapped_column(init=False)
    
    name: Mapped[str] = mapped_column(String(500), default='', comment='邮箱地址')

    country: Mapped[str] = mapped_column(String(500), default='', comment='国家/地区')

    labels: Mapped[str] = mapped_column(String(500), default='', comment='标签')

    email_num: Mapped[int] = mapped_column(Integer(), default=0, comment='邮箱数量')

    other_info: Mapped[str] = mapped_column(TEXT, default='', comment='其它信息')

    person_id: Mapped[int | None] = mapped_column(
        ForeignKey('sys_person.id', ondelete='SET NULL'), default=None, comment='所属人物ID'
    )
    person: Mapped[Union['Person', None]] = relationship(init=False, back_populates='mail_boxes')

    