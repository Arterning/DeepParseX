#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import BigInteger
from sqlalchemy.dialects.postgresql import TEXT
from backend.common.model import Base, id_key


class PersonRelation(Base):
    __tablename__ = 'sys_person_relation'
    id: Mapped[id_key] = mapped_column(BigInteger, init=False)
    person_id: Mapped[int | None] = mapped_column(
        ForeignKey('sys_person.id', ondelete='SET NULL'), default=None, index=True, comment='人物ID'
    )
    other_id: Mapped[int | None] = mapped_column(
        ForeignKey('sys_person.id', ondelete='SET NULL'), default=None, index=True, comment='人物ID'
    )

    # 关系类型
    relation_type: Mapped[str | None] = mapped_column(TEXT,default=None, comment='关系类型')

    # 关系权重
    weight: Mapped[int | None] = mapped_column(default=0, comment='关系权重')

    description : Mapped[str | None] = mapped_column(TEXT, default=None, comment='关系详情')
