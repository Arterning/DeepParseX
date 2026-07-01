#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务调度器

实体流水线和摘要翻译作为两个独立的 asyncio 持续循环并发运行，
任务完成后立即开始下一批，最大化硬件利用率。
新闻简报仍使用 APScheduler 按时触发。
"""

import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.core.conf import settings
from backend.common.log import log


scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

# 用于关闭时取消任务
_loop_tasks: list[asyncio.Task] = []


async def _pipeline_loop():
    """实体处理流水线持续循环（实体提取 → 图谱构建 → 实体关联）"""
    from backend.app.admin.service.scheduler_service import scheduler_service
    log.info(f"实体处理流水线循环已启动 (batch_size={settings.SCHEDULER_BATCH_SIZE})")
    while True:
        try:
            had_work = await scheduler_service.run_hourly_pipeline()
            if not had_work:
                await asyncio.sleep(settings.SCHEDULER_IDLE_SLEEP)
        except Exception as e:
            log.error(f"实体处理流水线循环异常: {repr(e)}")
            await asyncio.sleep(settings.SCHEDULER_IDLE_SLEEP)


async def _summary_loop():
    """摘要翻译持续循环"""
    from backend.app.admin.service.scheduler_service import scheduler_service
    log.info(f"摘要翻译循环已启动 (batch_size={settings.SCHEDULER_BATCH_SIZE})")
    while True:
        try:
            had_work = await scheduler_service.auto_generate_summary_and_translation()
            if not had_work:
                await asyncio.sleep(settings.SCHEDULER_IDLE_SLEEP)
        except Exception as e:
            log.error(f"摘要翻译循环异常: {repr(e)}")
            await asyncio.sleep(settings.SCHEDULER_IDLE_SLEEP)


async def start_scheduler():
    """启动调度器"""
    from backend.app.admin.service.config_service import config_service
    cfg = await config_service.get_merged_settings()

    if cfg.RSS_BRIEF_ENABLED:
        from backend.app.admin.service.news_briefing_service import news_briefing_service
        scheduler.add_job(
            news_briefing_service.run_daily_briefing,
            trigger=CronTrigger(hour=7, minute=0),
            id="daily_news_briefing",
            name="每日新闻简报",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        scheduler.start()
        log.info("已注册定时任务: 每日新闻简报 (每天 07:00)")

    if cfg.PIPELINE_LOOP_ENABLED:
        _loop_tasks.append(asyncio.create_task(_pipeline_loop()))

    if cfg.SUMMARY_LOOP_ENABLED:
        _loop_tasks.append(asyncio.create_task(_summary_loop()))

    log.info(
        f"已启动 {len(_loop_tasks)} 个并发处理循环 "
        f"(pipeline={cfg.PIPELINE_LOOP_ENABLED}, "
        f"summary={cfg.SUMMARY_LOOP_ENABLED}, "
        f"batch_size={cfg.SCHEDULER_BATCH_SIZE}, "
        f"idle_sleep={cfg.SCHEDULER_IDLE_SLEEP}s)"
    )


async def shutdown_scheduler():
    """关闭调度器"""
    for task in _loop_tasks:
        task.cancel()
    if _loop_tasks:
        await asyncio.gather(*_loop_tasks, return_exceptions=True)
        _loop_tasks.clear()

    if scheduler.running:
        scheduler.shutdown(wait=False)

    log.info("调度器已关闭")
