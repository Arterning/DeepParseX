#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import TEXT

from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.admin.model.sys_person_doc import sys_person_doc
from backend.app.admin.model.sys_person_org import sys_person_org
from backend.common.model import Base, id_key

# 其他名：人物原名、其他名称。
# 性别
# 所属组织：人物可属于多个组织。
# 职位：人物可有多个职位。
# 职业：人物的职业，如政客、律师、学生等。人物可以由多个职业。
# 出生日期：人物出生日期。
# 毕业院校/专业：人物毕业院校/专业。
# 人物标签：通过人物的基本信息分析出2-3个基本标签，其余标签由用户自由创建（只能看个人标签）。
# 人物简历：人物简历包含人物的简历信息。人物简历信息包括从公开渠道收集信息，从新闻媒体提取信息，从会议文件提取信息等。
# 人物黑料信息：人物黑料包含人物的黑料信息。

class Person(Base):
    """人物"""

    __tablename__ = 'sys_person'

    id: Mapped[id_key] = mapped_column(init=False)
    
    name: Mapped[str] = mapped_column(String(500), default='', comment='人物名称')
    
    other_name: Mapped[str] = mapped_column(String(500), default='', comment='其他名')
    
    gender: Mapped[str] = mapped_column(String(20), default='', comment='性别')
    
    organization: Mapped[str] = mapped_column(String(500), default='', comment='所属组织')
    
    position: Mapped[str] = mapped_column(String(500), default='', comment='职位')
    
    profession: Mapped[str] = mapped_column(String(500), default='', comment='职业')
    
    birth_date: Mapped[datetime | None] = mapped_column(default=None, comment='出生日期')
    
    school: Mapped[str] = mapped_column(String(500), default='', comment='毕业院校/专业')

    resume: Mapped[str] = mapped_column(TEXT, default='', comment='人物简历')

    mail_boxes: Mapped[list['MailBox']] = relationship(init=False, back_populates='person')

    docs: Mapped[list['SysDoc']] = relationship(
        init=False, secondary=sys_person_doc
    )

    orgs: Mapped[list['SysOrg']] = relationship(
        init=False, secondary=sys_person_org
    )
    
    # tags: Mapped[str] = mapped_column(String(), default='', comment='人物标签')
    
    # blacklist: Mapped[str] = mapped_column(String(), default='', comment='人物黑料信息')