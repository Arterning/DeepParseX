#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import TEXT

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key

# 新闻名称：分析出的新闻名称；
# 新闻简介：新闻的简要介绍；
# 新闻类型：新闻所属的类型，包括涉华、政治、民生、科技、自然灾害、公共应急、军事等。
# 发布来源：新闻发布的网站来源。
# 发布组织：新闻发布的组织。
# 新闻作者：新闻发布作者。
# 发布时间：新闻发布时间。
# 发布地点：新闻发布的物理地点。
# 新闻标签：新闻的备注标签。
# 新闻人物：新闻的成员，可以有多个，重点展示新闻的领导人员；
# 详情：链接字段，点击后查看新闻详情；
# 列表支持按照新闻名称或人物搜索新闻；
# 收藏新闻，将新闻进行收藏。

class News(Base):
    """新闻"""

    __tablename__ = 'sys_news'

    id: Mapped[id_key] = mapped_column(init=False)
    
    name: Mapped[str] = mapped_column(String(500), default='', comment='新闻标题')

    summary: Mapped[str] = mapped_column(TEXT, default='', comment='新闻简介')

    news_type: Mapped[str] = mapped_column(String(500), default='', comment='新闻类型')

    source: Mapped[str] = mapped_column(String(500), default='', comment='新闻来源')

    organization: Mapped[str] = mapped_column(String(500), default='', comment='新闻组织')

    author: Mapped[str] = mapped_column(String(500), default='', comment='新闻作者')

    time: Mapped[str] = mapped_column(String(500), default='', comment='新闻时间')

    location: Mapped[str] = mapped_column(String(500), default='', comment='新闻地点')

    tag: Mapped[str] = mapped_column(String(500), default='', comment='新闻标签')

    person: Mapped[str] = mapped_column(String(500), default='', comment='新闻人物')

    detail: Mapped[str] = mapped_column(TEXT, default='', comment='新闻详情')

    