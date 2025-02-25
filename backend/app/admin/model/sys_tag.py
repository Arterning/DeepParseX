#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import TEXT

from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.common.model import Base, id_key, UserMixin
from backend.app.admin.model.sys_tag_doc import sys_tag_doc
from backend.app.admin.model.sys_tag_person import sys_tag_person
from backend.app.admin.model.sys_tag_org import sys_tag_org
from backend.app.admin.model.sys_tag_subject import sys_tag_subject

class Tag(Base, UserMixin):
    """标签"""

    __tablename__ = 'sys_tag'

    id: Mapped[id_key] = mapped_column(init=False)
    
    name: Mapped[str] = mapped_column(sa.String(), default='', comment='标签名称')

    subjects: Mapped[list['Subject']] = relationship(
        init=False, secondary=sys_tag_subject
    )

    persons: Mapped[list['Person']] = relationship(
        init=False, secondary=sys_tag_person
    )

    orgs: Mapped[list['SysOrg']] = relationship(
        init=False, secondary=sys_tag_org
    )

    docs: Mapped[list['SysDoc']] = relationship(
        init=False, secondary=sys_tag_doc
    )
    