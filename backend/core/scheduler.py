#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APScheduler 定时任务调度器

用于管理应用内的定时任务
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from backend.core.conf import settings
from backend.common.log import log


# 创建调度器实例
scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")


def register_scheduled_jobs():
    """注册所有定时任务"""
    from backend.app.admin.service.news_briefing_service import news_briefing_service
    from backend.app.admin.service.doc_service import sys_doc_service
    from backend.app.admin.service.entity_service import entity_service

    if settings.RSS_BRIEF_ENABLED:
        # 每日新闻简报任务 - 每天上午7点执行
        scheduler.add_job(
            news_briefing_service.run_daily_briefing,
            trigger=CronTrigger(hour=7, minute=0),
            id="daily_news_briefing",
            name="每日新闻简报",
            replace_existing=True,
            misfire_grace_time=3600,  # 允许1小时的延迟执行
        )

        log.info("已注册定时任务: 每日新闻简报 (每天 07:00)")

    # 自动提取实体任务 - 每小时执行一次
    scheduler.add_job(
        sys_doc_service.auto_build_graph_for_docs,
        trigger=CronTrigger(minute=0),  # 每小时的第0分钟执行
        id="auto_build_graph",
        name="自动构建知识图谱",
        replace_existing=True,
        misfire_grace_time=1800,  # 允许30分钟的延迟执行
    )

    log.info("已注册定时任务: 自动构建知识图谱 (每小时一次)")

    # 自动关联实体并生成属性 - 每小时执行一次（在第30分钟执行，与知识图谱任务错开）
    scheduler.add_job(
        entity_service.auto_link_and_generate_properties,
        trigger=CronTrigger(minute=30),
        id="auto_link_and_generate_properties",
        name="自动关联实体并生成属性",
        replace_existing=True,
        misfire_grace_time=1800,
    )

    log.info("已注册定时任务: 自动关联实体并生成属性 (每小时一次)")


async def start_scheduler():
    """启动调度器"""
    register_scheduled_jobs()
    scheduler.start()
    log.info("定时任务调度器已启动")


async def shutdown_scheduler():
    """关闭调度器"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        log.info("定时任务调度器已关闭")
