#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import List, Any
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import TEXT, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.common.model import Base, id_key


class EntityType(Base):
    """实体类型"""

    __tablename__ = 'sys_entity_type'

    id: Mapped[id_key] = mapped_column(init=False)
    name: Mapped[str] = mapped_column(String(255), unique=True, comment='实体类型名称')
    description: Mapped[str | None] = mapped_column(TEXT, default=None, comment='实体类型描述')
    field_definition: Mapped[List[str] | None] = mapped_column(
        JSONB, default=None, comment='字段定义（字段名称数组）'
    )

    # 关联到实体表
    entities: Mapped[list['Entity']] = relationship(
        'Entity', back_populates='entity_type_rel', init=False
    )
