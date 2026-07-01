#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime

from pydantic import ConfigDict

from backend.common.schema import SchemaBase


class MailBoxSchemaBase(SchemaBase):

    name: str
    user_name: str | None = None
    country: str | None = None
    occupation: str | None = None
    organization: str | None = None
    job_title: str | None = None
    email_num: int | None = None
    labels: str | None = None
    other_info: str | None = None
    profile: str | None = None

    

class GetTagSimple(SchemaBase):
    """简化的标签信息，用于列表展示"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class CreateMailBoxParam(MailBoxSchemaBase):
    pass


class UpdateMailBoxParam(MailBoxSchemaBase):
    pass


class GetMailBoxListDetails(MailBoxSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    
    created_time: datetime
    updated_time: datetime | None = None

    tags: list[GetTagSimple] = []
    
class GetMailBoxDetails(MailBoxSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int

    created_time: datetime
    updated_time: datetime | None = None

    tags: list[GetTagSimple] = []


class MailMsgBrief(SchemaBase):
    """邮件简要信息"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    doc_id: int | None = None
    name: str | None = None
    subject: str | None = None
    translate_subject: str | None = None
    time: datetime | None = None
    sender: str | None = None
    receiver: str | None = None
    cc: str | None = None


class PersonEntityBrief(SchemaBase):
    """人物实体简要信息"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str | None = None
    description: str | None = None
    properties: dict | None = None
    source_doc_id: int | None = None
    source_doc_name: str | None = None


class GetMailBoxFullDetails(GetMailBoxDetails):
    """邮箱完整详情，包含邮件和人物实体"""
    sent_emails: list[MailMsgBrief] = []
    received_emails: list[MailMsgBrief] = []
    cc_emails: list[MailMsgBrief] = []
    person_entities: list[PersonEntityBrief] = []