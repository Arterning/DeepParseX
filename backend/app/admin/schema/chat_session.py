#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime

from pydantic import ConfigDict

from backend.common.schema import SchemaBase


# 消息相关 Schema
class MessageParam(SchemaBase):
    """创建或更新消息时使用的参数"""
    sender: str  # 'user' 或 'bot'
    content: str


class MessageDetails(SchemaBase):
    """返回消息详情"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    sender: str
    content: str
    created_time: datetime


# 会话相关 Schema
class ChatSessionSchemaBase(SchemaBase):
    topic: str
    create_user: int | None = None


class CreateChatSessionParam(ChatSessionSchemaBase):
    """创建会话参数（空会话，只有 topic）"""
    topic: str = "新对话"


class UpdateChatSessionParam(SchemaBase):
    """更新会话参数（包含 messages）"""
    topic: str | None = None
    messages: list[MessageParam] | None = None
    update_user: int | None = None


class GetChatSessionListDetails(SchemaBase):
    """会话列表详情（包含完整 messages）"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic: str
    messages: list[MessageDetails] = []
    created_time: datetime
    updated_time: datetime | None = None


class GetChatSessionDetails(SchemaBase):
    """会话详情（包含完整 messages）"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic: str
    messages: list[MessageDetails] = []
    created_time: datetime
    updated_time: datetime | None = None
    