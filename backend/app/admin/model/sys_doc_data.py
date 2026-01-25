#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Union
from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import JSON, TEXT

from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.common.model import Base, id_key


class SysDocData(Base):
    """文件数据"""

    __tablename__ = 'sys_doc_data'

    id: Mapped[id_key] = mapped_column(init=False)
    doc_id: Mapped[int | None] = mapped_column(
        ForeignKey('sys_doc.id', ondelete='CASCADE'), default=None, index=True, comment='文件ID'
    )

    doc: Mapped[Union['SysDoc', None]] = relationship(init=False, back_populates='doc_data')

    row: Mapped[JSON | None] = mapped_column(JSON, default=None, comment='行数据')
