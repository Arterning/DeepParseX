#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Union
from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import TEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.common.model import Base, UserMixin, id_key


class ChatSession(Base, UserMixin):
    """聊天会话表"""

    __tablename__ = 'sys_chat_session'

    id: Mapped[id_key] = mapped_column(init=False)
    
    topic: Mapped[str] = mapped_column(TEXT, default=None, comment='会话主题')

    messages: Mapped[list['ChatMessage']] = relationship(init=False, back_populates='session')
