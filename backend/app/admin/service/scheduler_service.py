#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时任务业务逻辑服务

集中管理所有由 APScheduler 调度的定时任务实现。
"""

import traceback
from datetime import datetime

from sqlalchemy import select, exists, func, or_, and_, update

from backend.app.admin.model import SysDoc
from backend.app.admin.model.sys_entity import Entity
from backend.app.admin.model.sys_entity_type import EntityType
from backend.app.admin.model.sys_doc_chunk import SysDocChunk
from backend.app.admin.model.sys_entity_doc import sys_entity_doc
from backend.common.log import log
from backend.core.conf import settings
from backend.database.db_pg import async_db_session
from backend.utils.timezone import timezone


async def _start_job_log(job_id: str, job_name: str) -> tuple[int | None, datetime]:
    """创建任务日志记录，返回 (log_id, started_at)"""
    from backend.app.admin.model.sys_scheduler_log import SysSchedulerLog
    started_at = timezone.now()
    try:
        async with async_db_session() as db:
            entry = SysSchedulerLog(job_id=job_id, job_name=job_name, started_at=started_at)
            db.add(entry)
            await db.commit()
            await db.refresh(entry)
            return entry.id, started_at
    except Exception as e:
        log.warning(f"创建任务日志失败: {repr(e)}")
        return None, started_at


async def _finish_job_log(log_id: int | None, started_at: datetime, processed: int, success: int, error: int):
    """更新任务日志记录"""
    if log_id is None:
        return
    from backend.app.admin.model.sys_scheduler_log import SysSchedulerLog
    finished_at = timezone.now()
    duration_ms = int((finished_at - started_at).total_seconds() * 1000)
    if error == 0:
        status = 'success'
    elif success > 0:
        status = 'partial_error'
    else:
        status = 'failed'
    try:
        async with async_db_session() as db:
            await db.execute(
                update(SysSchedulerLog)
                .where(SysSchedulerLog.id == log_id)
                .values(
                    finished_at=finished_at,
                    duration_ms=duration_ms,
                    processed=processed,
                    success=success,
                    error=error,
                    status=status,
                )
            )
            await db.commit()
    except Exception as e:
        log.warning(f"更新任务日志失败: {repr(e)}")


class SchedulerService:

    @staticmethod
    async def auto_extract_entities_for_docs() -> bool:
        """自动为没有关联实体的文档提取实体，返回本批是否有实际处理"""
        from backend.app.admin.service.doc_service import SysDocService, sys_doc_service

        DEFAULT_ENTITY_TYPE_DEFINITIONS = [
            {"type_name": "人物", "description": "人物实体", "fields": ["性别", "国籍", "组织", "职位", "联系方式"]},
            {"type_name": "组织", "description": "组织实体", "fields": ["类型", "国家"]},
            {"type_name": "事件", "description": "事件实体", "fields": ["时间", "地点", "参与者"]},
        ]

        log_id, started_at = None, None
        try:
            async with async_db_session() as db:
                stmt = (
                    select(SysDoc.id)
                    .where(SysDoc.entity_extracted != 1)
                    .where(SysDoc.status == 1)
                    .where(SysDoc.content.isnot(None))
                    .limit(settings.SCHEDULER_BATCH_SIZE)
                )
                result = await db.execute(stmt)
                doc_ids = [row[0] for row in result.all()]

            if not doc_ids:
                return False

            log_id, started_at = await _start_job_log('entity_extraction', '实体提取')

            log.info(f"开始为 {len(doc_ids)} 个文档提取实体")
            success_count = 0
            error_count = 0

            for doc_id in doc_ids:
                try:
                    entity_count = await SysDocService.extract_entities_by_types(
                        pk=doc_id, type_definitions=DEFAULT_ENTITY_TYPE_DEFINITIONS
                    )
                    await sys_doc_service.base_update(pk=doc_id, obj={'entity_extracted': 1})
                    success_count += 1
                    log.info(f"文档 {doc_id} 提取了 {entity_count} 个实体")
                except Exception as e:
                    error_count += 1
                    log.error(f"文档 {doc_id} 提取实体失败: {repr(e)}\n{traceback.format_exc()}")

            log.info(f"实体提取完成: 成功 {success_count} 个，失败 {error_count} 个")
            await _finish_job_log(log_id, started_at, len(doc_ids), success_count, error_count)
            return True

        except Exception as e:
            log.error(f"自动提取实体任务失败: {repr(e)}\n{traceback.format_exc()}")
            if log_id:
                await _finish_job_log(log_id, started_at, 0, 0, 1)
            return False

    @staticmethod
    async def auto_build_graph_for_docs() -> bool:
        """自动为文档构建知识图谱，返回本批是否有实际处理"""
        from backend.app.admin.service.doc_service import SysDocService, sys_doc_service

        log_id, started_at = None, None
        try:
            async with async_db_session() as db:
                result = await db.execute(select(EntityType.name))
                entity_type_names = [row[0] for row in result.all()]

            if not entity_type_names:
                log.info("没有定义实体类型，跳过知识图谱构建")
                return False

            async with async_db_session() as db:
                stmt = (
                    select(SysDoc.id)
                    .where(SysDoc.graph_extracted != 1)
                    .where(SysDoc.status == 1)
                    .where(SysDoc.content.isnot(None))
                    .limit(settings.SCHEDULER_BATCH_SIZE)
                )
                result = await db.execute(stmt)
                doc_ids = [row[0] for row in result.all()]

            if not doc_ids:
                return False

            log_id, started_at = await _start_job_log('graph_building', '知识图谱构建')

            log.info(f"开始为 {len(doc_ids)} 个文档构建知识图谱，实体类型: {entity_type_names}")
            success_count = 0
            error_count = 0

            for doc_id in doc_ids:
                try:
                    await SysDocService.build_graph(pk=doc_id, entity_types=entity_type_names)
                    await sys_doc_service.base_update(pk=doc_id, obj={'graph_extracted': 1})
                    success_count += 1
                    log.info(f"文档 {doc_id} 知识图谱构建完成")
                except Exception as e:
                    error_count += 1
                    log.error(f"文档 {doc_id} 知识图谱构建失败: {repr(e)}\n{traceback.format_exc()}")

            log.info(f"知识图谱构建完成: 成功 {success_count} 个，失败 {error_count} 个")
            await _finish_job_log(log_id, started_at, len(doc_ids), success_count, error_count)
            return True

        except Exception as e:
            log.error(f"自动构建知识图谱任务失败: {repr(e)}\n{traceback.format_exc()}")
            if log_id:
                await _finish_job_log(log_id, started_at, 0, 0, 1)
            return False

    @staticmethod
    async def auto_generate_summary_and_translation() -> bool:
        """自动为文档生成摘要和翻译，返回本批是否有实际处理"""
        from backend.app.admin.service.doc_service import sys_doc_service

        log_id, started_at = None, None
        try:
            async with async_db_session() as db:
                # 批量标记中文文档为无需翻译，避免其在统计中被误计为"未翻译"
                marked = await db.execute(
                    update(SysDoc)
                    .where(SysDoc.language == "中文")
                    .where(SysDoc.translation.is_(None))
                    .where(SysDoc.status == 1)
                    .values(translation="[中文原文，无需翻译]")
                )
                if marked.rowcount:
                    log.info(f"已标记 {marked.rowcount} 篇中文文档为无需翻译")
                await db.commit()

                needs_translation = and_(
                    SysDoc.translation.is_(None),
                    or_(SysDoc.language.is_(None), SysDoc.language != "中文")
                )
                stmt = (
                    select(SysDoc.id)
                    .where(or_(SysDoc.desc.is_(None), needs_translation))
                    .where(SysDoc.status == 1)
                    .where(SysDoc.content.isnot(None))
                    .limit(settings.SCHEDULER_BATCH_SIZE)
                )
                result = await db.execute(stmt)
                doc_ids = [row[0] for row in result.all()]

            if not doc_ids:
                return False

            log_id, started_at = await _start_job_log('summary_translation', '摘要与翻译生成')

            log.info(f"开始为 {len(doc_ids)} 个文档生成摘要和翻译")
            success_count = 0
            error_count = 0

            for doc_id in doc_ids:
                try:
                    doc = await sys_doc_service.get(pk=doc_id)

                    if not doc.desc:
                        await sys_doc_service.generate_summary(doc_id)
                        log.info(f"文档 {doc_id} 摘要生成完成")

                    if not doc.translation:
                        if doc.language and doc.language == "中文":
                            log.info(f"文档 {doc_id} 语言为中文，跳过翻译")
                        else:
                            await sys_doc_service.translate_pages(pk=doc_id, target_language="中文")
                            log.info(f"文档 {doc_id} 翻译完成")

                    success_count += 1
                except Exception as e:
                    error_count += 1
                    log.error(f"文档 {doc_id} 处理失败: {repr(e)}\n{traceback.format_exc()}")

            log.info(f"摘要和翻译生成完成: 成功 {success_count} 个，失败 {error_count} 个")
            await _finish_job_log(log_id, started_at, len(doc_ids), success_count, error_count)
            return True

        except Exception as e:
            log.error(f"自动生成摘要和翻译任务失败: {repr(e)}\n{traceback.format_exc()}")
            if log_id:
                await _finish_job_log(log_id, started_at, 0, 0, 1)
            return False

    @staticmethod
    async def auto_link_and_generate_properties() -> bool:
        """自动为未关联实体生成属性，返回本批是否有实际处理"""
        from backend.app.admin.service.entity_service import EntityService

        log_id, started_at = None, None
        try:
            async with async_db_session() as db:
                valid_types = await EntityService._get_valid_entity_types(db)

                linked_docs = (
                    select(sys_entity_doc.c.doc_id)
                    .where(sys_entity_doc.c.entity_id == Entity.id)
                    .correlate(Entity)
                )
                has_unlinked_mention = exists(
                    select(SysDocChunk.id).where(
                        SysDocChunk.chunk_vector.op('@@')(
                            func.plainto_tsquery('simple', func.lower(Entity.name))
                        ),
                        SysDocChunk.doc_id.notin_(linked_docs)
                    ).correlate(Entity)
                )
                stmt = (
                    select(Entity.id)
                    .where(Entity.name.isnot(None))
                    .where(func.length(Entity.name) >= 2)
                    .where(Entity.entity_type.in_(valid_types))
                    .where(or_(has_unlinked_mention, Entity.matched_chunks.is_(None), Entity.description.is_(None)))
                    .limit(settings.SCHEDULER_BATCH_SIZE)
                )
                result = await db.execute(stmt)
                entity_ids = [row[0] for row in result.all()]

            if not entity_ids:
                return False

            log_id, started_at = await _start_job_log('entity_linking', '实体关联与属性生成')

            log.info(f"开始为 {len(entity_ids)} 个未关联实体生成属性")
            success_count = 0
            error_count = 0

            for entity_id in entity_ids:
                try:
                    await EntityService.generate_properties_by_ai(pk=entity_id)
                    success_count += 1
                    log.info(f"实体 {entity_id} 属性生成完成")
                except Exception as e:
                    error_count += 1
                    log.error(f"实体 {entity_id} 属性生成失败: {repr(e)}\n{traceback.format_exc()}")

            log.info(f"未关联实体属性生成完成: 成功 {success_count} 个，失败 {error_count} 个")
            await _finish_job_log(log_id, started_at, len(entity_ids), success_count, error_count)
            return True

        except Exception as e:
            log.error(f"自动处理未关联实体任务失败: {repr(e)}\n{traceback.format_exc()}")
            if log_id:
                await _finish_job_log(log_id, started_at, 0, 0, 1)
            return False

    @staticmethod
    async def run_hourly_pipeline() -> bool:
        """实体处理流水线：实体提取 → 图谱构建 → 实体关联，返回是否有实际处理"""
        log.info("开始执行实体处理流水线")
        r1 = await SchedulerService.auto_extract_entities_for_docs()
        r2 = await SchedulerService.auto_build_graph_for_docs()
        r3 = await SchedulerService.auto_link_and_generate_properties()
        log.info("实体处理流水线执行完成")
        return r1 or r2 or r3


scheduler_service = SchedulerService()
