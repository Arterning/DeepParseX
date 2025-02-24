#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import TEXT

from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.common.model import Base, id_key
from backend.app.admin.model.sys_subject_doc import sys_subject_doc
from backend.app.admin.model.sys_subject_person import sys_subject_person
from backend.app.admin.model.sys_subject_org import sys_subject_org


class Subject(Base):
    """议题"""

    __tablename__ = 'sys_subject'

    id: Mapped[id_key] = mapped_column(init=False)
    
    name: Mapped[str] = mapped_column(sa.String(), default='', comment='议题名称')

    source: Mapped[str] = mapped_column(sa.String(), default='', comment='议题来源')

    content: Mapped[str | None] = mapped_column(TEXT, default=None, comment='议题概述')
    
    
    docs: Mapped[list['SysDoc']] = relationship(
        init=False, secondary=sys_subject_doc
    )

    persons: Mapped[list['Person']] = relationship(
        init=False, secondary=sys_subject_person
    )

    orgs: Mapped[list['SysOrg']] = relationship(
        init=False, secondary=sys_subject_org
    )