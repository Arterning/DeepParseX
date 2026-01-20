#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APScheduler 定时任务调度器

用于管理应用内的定时任务
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.common.log import log


# 创建调度器实例
scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")


def register_scheduled_jobs():
    """注册所有定时任务"""
    from backend.app.admin.service.news_briefing_service import news_briefing_service

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
