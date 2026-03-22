#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IOC（失陷指标）提取与管理服务

支持类型：ip / domain / url / md5 / sha1 / sha256 / email / cve
提取库：iocextract（需 pip install iocextract）
"""
import re
import traceback
from typing import Iterator

from backend.common.log import log
from backend.app.admin.crud.crud_ioc import ioc_dao
from backend.app.admin.schema.ioc import CreateIocParam, UpdateIocStatusParam, PromoteIocToEntityParam
from backend.app.admin.schema.entity import CreateEntityParam
from backend.database.db_pg import async_db_session

# ── 上下文窗口大小（提取IOC前后各N个字符） ──────────────────────────────────────
_CONTEXT_WINDOW = 120

# ── 正则备用（当 iocextract 未安装时使用） ──────────────────────────────────────
_RE_IPV4 = re.compile(
    r'\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b'
)
_RE_MD5 = re.compile(r'\b[0-9a-fA-F]{32}\b')
_RE_SHA1 = re.compile(r'\b[0-9a-fA-F]{40}\b')
_RE_SHA256 = re.compile(r'\b[0-9a-fA-F]{64}\b')
_RE_EMAIL = re.compile(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b')
_RE_CVE = re.compile(r'\bCVE-\d{4}-\d{4,}\b', re.IGNORECASE)
_RE_DOMAIN = re.compile(
    r'\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b'
)
_RE_URL = re.compile(
    r'https?://[^\s<>"\']+', re.IGNORECASE
)

# 排除私有/保留 IP 段
_PRIVATE_NETS = [
    re.compile(r'^10\.'),
    re.compile(r'^172\.(1[6-9]|2\d|3[01])\.'),
    re.compile(r'^192\.168\.'),
    re.compile(r'^127\.'),
    re.compile(r'^0\.'),
    re.compile(r'^255\.'),
]


def _is_private_ip(ip: str) -> bool:
    return any(p.match(ip) for p in _PRIVATE_NETS)


def _get_context(text: str, match: re.Match, window: int = _CONTEXT_WINDOW) -> str:
    start = max(0, match.start() - window)
    end = min(len(text), match.end() + window)
    snippet = text[start:end].replace('\n', ' ').strip()
    return snippet


def _extract_with_iocextract(text: str) -> Iterator[tuple[str, str, bool]]:
    """使用 iocextract 提取，yield (ioc_type, value, is_defanged)"""
    import iocextract
    for url in iocextract.extract_urls(text, refang=False):
        defanged = url != iocextract.refang_url(url)
        yield 'url', iocextract.refang_url(url).lower(), defanged
    for ip in iocextract.extract_ips(text, refang=False):
        refanged = iocextract.refang_ipv4(ip)
        if refanged and not _is_private_ip(refanged):
            yield 'ip', refanged, ip != refanged
    for email in iocextract.extract_emails(text, refang=False):
        yield 'email', iocextract.refang_email(email).lower(), False
    for h in iocextract.extract_hashes(text):
        length = len(h)
        if length == 32:
            yield 'md5', h.lower(), False
        elif length == 40:
            yield 'sha1', h.lower(), False
        elif length == 64:
            yield 'sha256', h.lower(), False


def _extract_with_regex(text: str) -> Iterator[tuple[str, str, bool]]:
    """纯正则备用方案，yield (ioc_type, value, is_defanged)"""
    seen: set[tuple[str, str]] = set()

    def _emit(ioc_type: str, value: str, defanged: bool = False):
        key = (ioc_type, value)
        if key not in seen:
            seen.add(key)
            yield ioc_type, value, defanged

    # SHA256 优先（避免被MD5/SHA1误匹配）
    for m in _RE_SHA256.finditer(text):
        yield from _emit('sha256', m.group().lower())
    for m in _RE_SHA1.finditer(text):
        v = m.group().lower()
        if ('sha256', v) not in seen:
            yield from _emit('sha1', v)
    for m in _RE_MD5.finditer(text):
        v = m.group().lower()
        if ('sha256', v) not in seen and ('sha1', v) not in seen:
            yield from _emit('md5', v)

    for m in _RE_URL.finditer(text):
        yield from _emit('url', m.group().lower())
    for m in _RE_IPV4.finditer(text):
        if not _is_private_ip(m.group()):
            yield from _emit('ip', m.group())
    for m in _RE_EMAIL.finditer(text):
        yield from _emit('email', m.group().lower())
    for m in _RE_CVE.finditer(text):
        yield from _emit('cve', m.group().upper())


def _extract_iocs_from_text(text: str) -> list[tuple[str, str, bool]]:
    """
    返回 [(ioc_type, value, is_defanged), ...]，去重
    优先使用 iocextract，不可用时降级到正则
    """
    if not text or not text.strip():
        return []
    try:
        import iocextract  # noqa: F401
        results = list(_extract_with_iocextract(text))
        # iocextract 不提取 CVE，补充正则
        for m in _RE_CVE.finditer(text):
            results.append(('cve', m.group().upper(), False))
    except ImportError:
        log.warning('iocextract 未安装，使用正则备用方案提取 IOC')
        results = list(_extract_with_regex(text))

    # 全局去重
    seen: set[tuple[str, str]] = set()
    deduped = []
    for item in results:
        key = (item[0], item[1])
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped


class IocService:

    @staticmethod
    async def extract_from_doc(doc_id: int, content: str) -> int:
        """
        从文档内容提取 IOC 并批量写库。
        调用方式：asyncio.create_task(ioc_service.extract_from_doc(...))
        返回写入条数。
        """
        try:
            raw_iocs = _extract_iocs_from_text(content)
            if not raw_iocs:
                return 0

            # 为每条 IOC 截取上下文
            params: list[CreateIocParam] = []
            for ioc_type, value, is_defanged in raw_iocs:
                # 在原文中找第一个匹配位置以取上下文
                pattern = re.escape(value)
                m = re.search(pattern, content, re.IGNORECASE)
                ctx = _get_context(content, m) if m else None

                params.append(CreateIocParam(
                    doc_id=doc_id,
                    ioc_type=ioc_type,
                    value=value,
                    context=ctx,
                    is_defanged=is_defanged,
                    status=0,
                ))

            async with async_db_session() as db:
                count = await ioc_dao.bulk_create(db, params)
                await db.commit()

            log.info(f'[IOC] 文档 {doc_id} 提取完成，写入 {count} 条')

            # 对 IP 类型 IOC 触发地理坐标关联
            await ioc_service._trigger_geo_for_ip_iocs(doc_id=doc_id, params=params)

            return count
        except Exception as e:
            log.error(f'[IOC] 文档 {doc_id} 提取失败: {repr(e)}\n{traceback.format_exc()}')
            return 0

    @staticmethod
    async def get(pk: int):
        async with async_db_session() as db:
            return await ioc_dao.get(db, pk)

    @staticmethod
    async def get_select(
        doc_id: int | None = None,
        ioc_type: str | None = None,
        value: str | None = None,
        status: int | None = None,
    ):
        async with async_db_session() as db:
            return await ioc_dao.get_list(db, doc_id=doc_id, ioc_type=ioc_type, value=value, status=status)

    @staticmethod
    async def update_status(pk: int, obj: UpdateIocStatusParam) -> int:
        async with async_db_session() as db:
            count = await ioc_dao.update_status(db, pk, obj)
            await db.commit()
            return count

    @staticmethod
    async def delete(pk: list[int]) -> int:
        async with async_db_session() as db:
            count = await ioc_dao.delete(db, pk)
            await db.commit()
            return count

    @staticmethod
    async def promote_to_entity(pk: int, obj: PromoteIocToEntityParam) -> int:
        """
        将 IOC 提升为 Entity，写入 sys_entity 并更新 ioc.entity_id。
        返回新建 entity 的 ID。
        """
        from backend.app.admin.crud.crud_entity import entity_dao

        async with async_db_session() as db:
            ioc = await ioc_dao.get(db, pk)
            if not ioc:
                from backend.common.exception import errors
                raise errors.NotFoundError(msg='IOC 不存在')

            entity_param = CreateEntityParam(
                name=ioc.value,
                description=obj.description or f'{ioc.ioc_type.upper()} indicator: {ioc.value}',
                entity_type=obj.entity_type,
                properties={
                    'ioc_type': ioc.ioc_type,
                    'is_defanged': ioc.is_defanged,
                    'source': 'ioc_extraction',
                },
            )
            entity = await entity_dao.create(db, entity_param)
            await db.flush()

            await ioc_dao.update_entity_id(db, pk, entity.id)
            await db.commit()
            return entity.id

    @staticmethod
    async def _trigger_geo_for_ip_iocs(doc_id: int, params: list[CreateIocParam]) -> None:
        """对本次写入的 IP IOC 查询已保存记录并触发 GeoIP"""
        from backend.app.admin.service.geo_service import geo_service
        ip_values = [p.value for p in params if p.ioc_type == 'ip']
        if not ip_values:
            return
        async with async_db_session() as db:
            for ip in ip_values:
                ioc = await ioc_dao.get_by_doc_type_value(db, doc_id, 'ip', ip)
                if ioc:
                    asyncio.create_task(geo_service.create_from_ip_ioc(ioc.id, ip))

    @staticmethod
    async def re_extract(doc_id: int) -> int:
        """重新提取文档 IOC（先删后提取）"""
        from backend.app.admin.service.doc_service import sys_doc_service
        async with async_db_session() as db:
            await ioc_dao.delete_by_doc(db, doc_id)
            await db.commit()
        doc = await sys_doc_service.get(pk=doc_id)
        if not doc or not doc.content:
            return 0
        return await ioc_service.extract_from_doc(doc_id=doc_id, content=doc.content)


ioc_service = IocService()
