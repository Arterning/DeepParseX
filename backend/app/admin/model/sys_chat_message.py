#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Union
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import TEXT, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.common.model import Base, UserMixin, id_key


class ChatMessage(Base, UserMixin):
    """聊天记录表"""

    __tablename__ = 'sys_chat_message'

    id: Mapped[id_key] = mapped_column(init=False)
    sender: Mapped[str | None] = mapped_column(String(50), default=None, comment='发送者')
    content: Mapped[str | None] = mapped_column(TEXT, default=None, comment='内容')
    chunks: Mapped[list | None] = mapped_column(JSONB, default=None, comment='引用文件列表')

    session_id: Mapped[int | None] = mapped_column(
        ForeignKey('sys_chat_session.id', ondelete='SET NULL'), default=None, comment='会话关联ID'
    )
    session: Mapped[Union['ChatSession', None]] = relationship(init=False, back_populates='messages')
    