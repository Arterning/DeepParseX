#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Union

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import TEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.common.model import Base, id_key, UserMixin


class SysDocDir(Base, UserMixin):
    """文件目录"""

    __tablename__ = 'sys_doc_dir'

    id: Mapped[id_key] = mapped_column(init=False)
    name: Mapped[str] = mapped_column(String(255), default='', comment='目录名称')
    level: Mapped[int] = mapped_column(default=0, comment='目录层级')
    sort: Mapped[int] = mapped_column(default=0, comment='排序')
    remark: Mapped[str | None] = mapped_column(TEXT, default=None, comment='备注')
    del_flag: Mapped[bool] = mapped_column(default=False, comment='删除标志（0删除 1存在）')

    # 父级目录
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey('sys_doc_dir.id', ondelete='SET NULL'), default=None, index=True, comment='父目录ID'
    )
    parent: Mapped[Union['SysDocDir', None]] = relationship(init=False, back_populates='children', remote_side=[id])
    children: Mapped[list['SysDocDir'] | None] = relationship(init=False, back_populates='parent')

    # 目录下的文件
    docs: Mapped[list['SysDoc']] = relationship(init=False, back_populates='doc_dir')
