#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime

from pydantic import ConfigDict

from backend.common.schema import SchemaBase


# 引用文件信息 Schema
class ReferenceInfo(SchemaBase):
    """按文件分组的引用信息"""
    ref_index: int | None = None
    doc_id: int | None = None
    doc_name: str | None = None
    content_preview: str | None = None


# 消息相关 Schema
class MessageParam(SchemaBase):
    """创建或更新消息时使用的参数"""
    sender: str  # 'user' 或 'bot'
    content: str
    chunks: list[ReferenceInfo] | None = None  # 引用文件列表，仅 bot 回复时有值


class MessageDetails(SchemaBase):
    """返回消息详情"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    sender: str
    content: str
    chunks: list[ReferenceInfo] | None = None  # 引用文件列表
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
