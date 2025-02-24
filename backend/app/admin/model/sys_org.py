#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
from sqlalchemy import Integer, String
from sqlalchemy.schema import Index
from sqlalchemy.dialects.postgresql import TEXT, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.common.model import Base, id_key

from backend.app.admin.model.sys_org_doc import sys_org_doc
from backend.app.admin.model.sys_org_assets import sys_org_assets
from backend.app.admin.model.sys_person_org import sys_person_org


# 组织名称：分析出的组织名称。
# 组织重点人物：展示组织的领导人员。
# 组织文件数量：经过汇总分析后，组织的文件数量。
# 详情：链接字段，点击后查看组织详情。
# 创建时间：组织的创建时间。
# 组织地点：组织的当前地址。
# 机构简介：组织的简要情况介绍。
# 机构标签：组织的标签。

class SysOrg(Base):
    """组织"""

    __tablename__ = 'sys_org'

    id: Mapped[id_key] = mapped_column(init=False)
    
    org_name: Mapped[str | None] = mapped_column(TEXT,default=None, comment='组织名称')
    org_file_nums: Mapped[int | None] = mapped_column(Integer,default=None, comment='组织文件数量')
    org_assets_nums: Mapped[int | None] = mapped_column(Integer,default=None, comment='组织资产数量')
    org_desc: Mapped[str | None] = mapped_column(TEXT,default=None, comment='组织描述')
    detail : Mapped[str | None] = mapped_column(TEXT,default=None, comment='详情')
    create_time: Mapped[datetime | None] = mapped_column(default=None, comment='创建时间')
    org_location: Mapped[str | None] = mapped_column(TEXT,default=None, comment='组织地点')
    org_introduce: Mapped[str | None] = mapped_column(TEXT,default=None, comment='组织简介')
    
    # org_tag: Mapped[str | None] = mapped_column(TEXT,default=None, comment='组织标签')

    docs: Mapped[list['SysDoc']] = relationship(
        init=False, secondary=sys_org_doc
    )

    persons: Mapped[list['Person']] = relationship(
        init=False, secondary=sys_person_org
    )

    assets: Mapped[list['SysAssets']] = relationship(
        init=False, secondary=sys_org_assets
    )
    