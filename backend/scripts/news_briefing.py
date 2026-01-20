#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新闻聚合与AI简报生成脚本

功能:
1. 初始化RSS订阅源（如果为空）
2. 从RSS源抓取文章并保存到sys_doc表
3. 使用AI生成每日简报

用法:
    python -m scripts.news_briefing
"""

import asyncio
import sys

# 添加项目根目录到路径
sys.path.append('../')

from backend.app.admin.service.news_briefing_service import news_briefing_service
from backend.common.log import log


async def main():
    """主函数"""
    log.info("=" * 50)
    log.info("新闻聚合与AI简报生成脚本")
    log.info("=" * 50)

    briefing = await news_briefing_service.run_daily_briefing()

    if briefing and briefing.content:
        # 打印简报内容预览
        log.info("\n简报内容预览:")
        log.info("-" * 50)
        preview = briefing.content[:1000] + "..." if len(briefing.content) > 1000 else briefing.content
        print(preview)

    log.info("\n脚本执行完成!")


if __name__ == "__main__":
    asyncio.run(main())
