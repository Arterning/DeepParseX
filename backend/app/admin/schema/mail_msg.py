#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class MailMsgSchemaBase(SchemaBase):
  name: str 
  subject: str | None = None
  original: str | None = None
  zh_content: str | None = None
  zh_subject: str | None = None
  time: datetime | None = None
  category: str | None = None
  sender: str | None = None
  receiver:str | None = None
  cc: str | None = None
  bcc: str | None = None
  doc_id: int | None = None
  doc_name: str | None = None
  from_row: str | None = None
  to_row: str | None = None
  cc_row: str | None = None
  bcc_row: str | None = None
  doc_dir_id: int | None = None
  attachments: list[dict] | None = None
  create_user: int | None = None
  detection_result: int | None = None
  message_id: str | None = None
  in_reply_to: str | None = None
  thread_id: str | None = None
  mail_box_id: int | None = None

    


class CreateMailMsgParam(MailMsgSchemaBase):
    pass


class UpdateMailMsgParam(MailMsgSchemaBase):
    pass


class GetMailMsgListDetails(MailMsgSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    original: str | None = Field(default=None, exclude=True)
    zh_content: str | None = Field(default=None, exclude=True)
    zh_subject: str | None = Field(default=None, exclude=True)
    id: int
    
    created_time: datetime
    updated_time: datetime | None = None
    
class GetMailMsgDetails(MailMsgSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    
    created_time: datetime
    updated_time: datetime | None = None