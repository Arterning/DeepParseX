#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy import String, ForeignKey, BIGINT, Float, Index
from sqlalchemy.dialects.postgresql import TEXT, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.common.model import Base, id_key


class GeoPoint(Base):
    """地理坐标点"""

    __tablename__ = 'sys_geo_point'

    id: Mapped[id_key] = mapped_column(init=False)

    source_type: Mapped[str] = mapped_column(
        String(20), comment='来源类型: exif / ip_ioc'
    )

    # 来源：文档（EXIF）
    doc_id: Mapped[int | None] = mapped_column(
        BIGINT, ForeignKey('sys_doc.id', ondelete='CASCADE'), default=None, index=True, comment='来源文档ID'
    )
    # 来源：IOC（IP 归属地）
    ioc_id: Mapped[int | None] = mapped_column(
        BIGINT, ForeignKey('sys_ioc.id', ondelete='CASCADE'), default=None, index=True, comment='来源IOC ID'
    )

    # 坐标（WGS84）
    lat: Mapped[float | None] = mapped_column(Float, default=None, comment='纬度 WGS84')
    lng: Mapped[float | None] = mapped_column(Float, default=None, comment='经度 WGS84')
    altitude: Mapped[float | None] = mapped_column(Float, default=None, comment='海拔（米），仅 EXIF 有')

    # 地名（GeoLite2 / 反向 Geocoding 后填入）
    country: Mapped[str | None] = mapped_column(String(100), default=None, comment='国家')
    city: Mapped[str | None] = mapped_column(String(100), default=None, comment='城市')

    accuracy: Mapped[str | None] = mapped_column(
        String(20), default=None, comment='精度级别: exact(EXIF) / city(IP归属)'
    )

    # EXIF 原始数据（调试用）
    raw_exif: Mapped[dict | None] = mapped_column(JSONB, default=None, comment='EXIF GPS 原始字段')

    # 关联
    doc: Mapped['SysDoc'] = relationship('SysDoc', init=False, lazy='noload')
    ioc: Mapped['IocRecord'] = relationship('IocRecord', init=False, lazy='noload')

    __table_args__ = (
        Index('ix_geo_point_lat_lng', 'lat', 'lng'),
    )
