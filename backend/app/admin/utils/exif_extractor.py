#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片 EXIF GPS 元数据提取工具

支持格式：JPG / JPEG / PNG（带 EXIF）/ HEIC（需安装 pillow-heif）
坐标系：WGS84（GPS 标准）
"""
from __future__ import annotations

import struct
from typing import Any


def _dms_to_decimal(dms: tuple, ref: str) -> float:
    """
    将度分秒（DMS）转换为十进制度（DD）

    dms: ((度分子, 度分母), (分分子, 分分母), (秒分子, 秒分母))
    ref: 'N'/'S'/'E'/'W'
    """
    def _ratio(val) -> float:
        # Pillow >= 9.1 返回 IFDRational，老版本返回 tuple
        if hasattr(val, 'numerator'):
            return val.numerator / val.denominator if val.denominator else 0.0
        if isinstance(val, tuple) and len(val) == 2:
            return val[0] / val[1] if val[1] else 0.0
        return float(val)

    degrees = _ratio(dms[0])
    minutes = _ratio(dms[1])
    seconds = _ratio(dms[2])
    decimal = degrees + minutes / 60.0 + seconds / 3600.0
    if ref in ('S', 'W'):
        decimal = -decimal
    return round(decimal, 7)


def _extract_gps_pillow(image_bytes: bytes) -> dict[str, Any] | None:
    """使用 Pillow 提取 GPS EXIF 数据"""
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS

    try:
        from io import BytesIO
        img = Image.open(BytesIO(image_bytes))
        exif_data = img._getexif()
        if not exif_data:
            return None

        # 找到 GPS IFD（tag id = 34853）
        gps_ifd_tag = next(
            (tag_id for tag_id, name in TAGS.items() if name == 'GPSInfo'), None
        )
        if gps_ifd_tag is None or gps_ifd_tag not in exif_data:
            return None

        gps_raw = exif_data[gps_ifd_tag]
        gps = {GPSTAGS.get(k, k): v for k, v in gps_raw.items()}

        lat = gps.get('GPSLatitude')
        lat_ref = gps.get('GPSLatitudeRef', 'N')
        lng = gps.get('GPSLongitude')
        lng_ref = gps.get('GPSLongitudeRef', 'E')
        alt = gps.get('GPSAltitude')
        alt_ref = gps.get('GPSAltitudeRef', 0)

        if not lat or not lng:
            return None

        lat_dd = _dms_to_decimal(lat, lat_ref)
        lng_dd = _dms_to_decimal(lng, lng_ref)

        altitude = None
        if alt is not None:
            try:
                alt_val = float(alt.numerator) / float(alt.denominator) if hasattr(alt, 'numerator') else float(alt[0]) / float(alt[1])
                altitude = round(-alt_val if alt_ref == 1 else alt_val, 2)
            except Exception:
                pass

        return {
            'lat': lat_dd,
            'lng': lng_dd,
            'altitude': altitude,
            'raw': {k: str(v) for k, v in gps.items()},
        }
    except Exception:
        return None


def _extract_gps_heic(image_bytes: bytes) -> dict[str, Any] | None:
    """使用 pillow-heif 提取 HEIC GPS 数据"""
    try:
        import pillow_heif
        from io import BytesIO

        pillow_heif.register_heif_opener()
        from PIL import Image
        img = Image.open(BytesIO(image_bytes))
        return _extract_gps_pillow_from_img(img)
    except ImportError:
        return None
    except Exception:
        return None


def _extract_gps_pillow_from_img(img) -> dict[str, Any] | None:
    """从已打开的 Pillow Image 对象提取 GPS"""
    from PIL.ExifTags import TAGS, GPSTAGS
    try:
        exif_data = img._getexif()
        if not exif_data:
            return None
        gps_ifd_tag = next(
            (tag_id for tag_id, name in TAGS.items() if name == 'GPSInfo'), None
        )
        if gps_ifd_tag is None or gps_ifd_tag not in exif_data:
            return None
        gps_raw = exif_data[gps_ifd_tag]
        gps = {GPSTAGS.get(k, k): v for k, v in gps_raw.items()}
        lat = gps.get('GPSLatitude')
        lat_ref = gps.get('GPSLatitudeRef', 'N')
        lng = gps.get('GPSLongitude')
        lng_ref = gps.get('GPSLongitudeRef', 'E')
        alt = gps.get('GPSAltitude')
        alt_ref = gps.get('GPSAltitudeRef', 0)
        if not lat or not lng:
            return None
        lat_dd = _dms_to_decimal(lat, lat_ref)
        lng_dd = _dms_to_decimal(lng, lng_ref)
        altitude = None
        if alt is not None:
            try:
                alt_val = float(alt.numerator) / float(alt.denominator) if hasattr(alt, 'numerator') else float(alt[0]) / float(alt[1])
                altitude = round(-alt_val if alt_ref == 1 else alt_val, 2)
            except Exception:
                pass
        return {
            'lat': lat_dd,
            'lng': lng_dd,
            'altitude': altitude,
            'raw': {k: str(v) for k, v in gps.items()},
        }
    except Exception:
        return None


def extract_gps(image_bytes: bytes, file_suffix: str) -> dict[str, Any] | None:
    """
    统一入口：从图片字节中提取 GPS 信息。

    返回：
        {
            'lat': float,       # 纬度（WGS84 十进制度）
            'lng': float,       # 经度（WGS84 十进制度）
            'altitude': float,  # 海拔（米），可能为 None
            'raw': dict,        # 原始 EXIF GPS 字段（字符串化）
        }
    或 None（无 GPS 数据 / 不支持格式）
    """
    suffix = file_suffix.lower()
    if suffix in ('.heic', '.heif'):
        return _extract_gps_heic(image_bytes)
    elif suffix in ('.jpg', '.jpeg', '.png', '.tiff', '.tif', '.webp'):
        return _extract_gps_pillow(image_bytes)
    return None
