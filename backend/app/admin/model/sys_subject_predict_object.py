#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Union
from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import TEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.common.model import Base, id_key


class SubjectPredictObject(Base):
    """主谓宾三元组"""

    __tablename__ = 'sys_subject_predict_object'

    id: Mapped[id_key] = mapped_column(init=False)
    subject: Mapped[str | None] = mapped_column(TEXT, default=None, comment='主语')
    predict: Mapped[str | None] = mapped_column(String(255), default=None, comment='谓语')
    object: Mapped[str | None] = mapped_column(TEXT, default=None, comment='宾语')

    doc_id: Mapped[int | None] = mapped_column(
        ForeignKey('sys_doc.id', ondelete='CASCADE'), default=None, index=True, comment='文件ID'
    )

    doc: Mapped[Union['SysDoc', None]] = relationship(init=False, back_populates='doc_spos')