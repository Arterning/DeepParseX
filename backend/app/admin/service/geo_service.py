#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
地理坐标服务

来源1: 图片 EXIF GPS（JPG / HEIC）
来源2: IP IOC → MaxMind GeoLite2 本地库（可选，未配置时坐标留空）
"""
import asyncio
import traceback

from backend.common.log import log
from backend.app.admin.crud.crud_geo_point import geo_point_dao
from backend.app.admin.schema.geo_point import CreateGeoPointParam
from backend.database.db_pg import async_db_session


# ── MaxMind GeoLite2 懒加载（未安装 / 未配置时静默跳过） ────────────────────────
_geoip_reader = None
_geoip_loaded = False


def _get_geoip_reader():
    global _geoip_reader, _geoip_loaded
    if _geoip_loaded:
        return _geoip_reader
    _geoip_loaded = True
    try:
        import geoip2.database
        from backend.core.conf import settings
        db_path = getattr(settings, 'GEOIP_DB_PATH', None)
        if db_path:
            _geoip_reader = geoip2.database.Reader(db_path)
            log.info(f'[Geo] GeoLite2 数据库已加载: {db_path}')
        else:
            log.info('[Geo] GEOIP_DB_PATH 未配置，IP 归属地坐标功能禁用')
    except ImportError:
        log.info('[Geo] geoip2 未安装，IP 归属地坐标功能禁用')
    except Exception as e:
        log.warning(f'[Geo] GeoLite2 加载失败: {repr(e)}')
    return _geoip_reader


def _lookup_ip_sync(ip: str) -> dict | None:
    """同步查询 IP 归属地，返回 {lat, lng, country, city} 或 None"""
    reader = _get_geoip_reader()
    if not reader:
        return None
    try:
        response = reader.city(ip)
        lat = response.location.latitude
        lng = response.location.longitude
        if lat is None or lng is None:
            return None
        return {
            'lat': lat,
            'lng': lng,
            'country': response.country.name or response.country.iso_code,
            'city': response.city.name,
        }
    except Exception:
        return None


class GeoService:

    @staticmethod
    async def extract_from_image(doc_id: int, file_bytes: bytes, file_suffix: str) -> bool:
        """
        从图片 EXIF 提取 GPS，写入 sys_geo_point。
        已有记录则跳过（幂等）。
        返回是否成功提取到坐标。
        """
        try:
            from backend.app.admin.utils.exif_extractor import extract_gps

            gps = await asyncio.to_thread(extract_gps, file_bytes, file_suffix)
            if not gps:
                return False

            async with async_db_session() as db:
                existing = await geo_point_dao.get_by_doc(db, doc_id)
                if existing:
                    return True

                param = CreateGeoPointParam(
                    doc_id=doc_id,
                    source_type='exif',
                    lat=gps['lat'],
                    lng=gps['lng'],
                    altitude=gps.get('altitude'),
                    accuracy='exact',
                    raw_exif=gps.get('raw'),
                )
                await geo_point_dao.create(db, param)
                await db.commit()

            log.info(f'[Geo] 文档 {doc_id} EXIF GPS 提取成功: ({gps["lat"]}, {gps["lng"]})')
            return True
        except Exception as e:
            log.error(f'[Geo] 文档 {doc_id} EXIF 提取失败: {repr(e)}\n{traceback.format_exc()}')
            return False

    @staticmethod
    async def create_from_ip_ioc(ioc_id: int, ip: str) -> bool:
        """
        根据 IP IOC 查询归属地坐标，写入 sys_geo_point。
        未配置 GeoLite2 时，写入一条无坐标的占位记录（ioc_id 关联保留）。
        """
        try:
            async with async_db_session() as db:
                existing = await geo_point_dao.get_by_ioc(db, ioc_id)
                if existing:
                    return True

            # 在线程池中执行同步 GeoIP 查询
            geo = await asyncio.to_thread(_lookup_ip_sync, ip)

            param = CreateGeoPointParam(
                ioc_id=ioc_id,
                source_type='ip_ioc',
                lat=geo['lat'] if geo else None,
                lng=geo['lng'] if geo else None,
                country=geo['country'] if geo else None,
                city=geo['city'] if geo else None,
                accuracy='city' if geo else None,
            )

            async with async_db_session() as db:
                await geo_point_dao.create(db, param)
                await db.commit()

            if geo:
                log.info(f'[Geo] IOC {ioc_id} IP={ip} 归属地: {geo.get("city")}, {geo.get("country")} ({geo["lat"]}, {geo["lng"]})')
            else:
                log.info(f'[Geo] IOC {ioc_id} IP={ip} 无归属地数据，已建立关联占位')
            return True
        except Exception as e:
            log.error(f'[Geo] IOC {ioc_id} IP 归属地写入失败: {repr(e)}\n{traceback.format_exc()}')
            return False

    @staticmethod
    async def get_map_points(
        source_type: str | None = None,
        doc_id: int | None = None,
    ) -> list[dict]:
        """获取所有带坐标的点，供前端地图渲染"""
        async with async_db_session() as db:
            points = await geo_point_dao.get_all_with_coords(db)

        result = []
        for p in points:
            if source_type and p.source_type != source_type:
                continue
            if doc_id and p.doc_id != doc_id:
                continue
            result.append({
                'id': p.id,
                'lat': p.lat,
                'lng': p.lng,
                'altitude': p.altitude,
                'source_type': p.source_type,
                'doc_id': p.doc_id,
                'ioc_id': p.ioc_id,
                'country': p.country,
                'city': p.city,
                'accuracy': p.accuracy,
            })
        return result

    @staticmethod
    async def get_list(
        doc_id: int | None = None,
        ioc_id: int | None = None,
        source_type: str | None = None,
    ):
        async with async_db_session() as db:
            return await geo_point_dao.get_list(db, doc_id=doc_id, ioc_id=ioc_id, source_type=source_type)

    @staticmethod
    async def delete(pk: list[int]) -> int:
        async with async_db_session() as db:
            count = await geo_point_dao.delete(db, pk)
            await db.commit()
            return count


geo_service = GeoService()
