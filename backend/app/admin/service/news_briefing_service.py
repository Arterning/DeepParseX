#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新闻聚合与AI简报生成服务

提供RSS订阅源管理、文章抓取和AI简报生成功能
"""

import asyncio
import hashlib
from datetime import datetime, timedelta

import feedparser
import httpx
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin.model.sys_briefing import Briefing
from backend.app.admin.model.sys_doc import SysDoc
from backend.app.admin.model.sys_rss_source import RssSource
from backend.app.admin.service.llm_service import llm_service
from backend.common.log import log
from backend.database.db_pg import async_db_session
from backend.utils.timezone import timezone


# 默认的高质量RSS订阅源
DEFAULT_RSS_SOURCES = [
    # 中文科技新闻
    {
        "name": "36氪",
        "url": "https://36kr.com/feed",
        "category": "tech",
        "language": "zh",
        "description": "中国领先的科技媒体",
        "priority": 10
    },
    {
        "name": "少数派",
        "url": "https://sspai.com/feed",
        "category": "tech",
        "language": "zh",
        "description": "高质量数字生活指南",
        "priority": 8
    },
    {
        "name": "InfoQ中文",
        "url": "https://www.infoq.cn/feed",
        "category": "tech",
        "language": "zh",
        "description": "软件开发技术资讯",
        "priority": 9
    },
    # 英文科技新闻
    {
        "name": "Hacker News",
        "url": "https://hnrss.org/frontpage",
        "category": "tech",
        "language": "en",
        "description": "Y Combinator技术社区",
        "priority": 10
    },
    {
        "name": "TechCrunch",
        "url": "https://techcrunch.com/feed/",
        "category": "tech",
        "language": "en",
        "description": "科技创业媒体",
        "priority": 9
    },
    {
        "name": "The Verge",
        "url": "https://www.theverge.com/rss/index.xml",
        "category": "tech",
        "language": "en",
        "description": "科技与文化",
        "priority": 8
    },
    # 财经新闻
    {
        "name": "华尔街见闻",
        "url": "https://wallstreetcn.com/rss/news",
        "category": "finance",
        "language": "zh",
        "description": "全球财经资讯",
        "priority": 9
    },
    # AI相关
    {
        "name": "AI News",
        "url": "https://buttondown.email/ainews/rss",
        "category": "ai",
        "language": "en",
        "description": "AI领域最新动态",
        "priority": 10
    },
    # 综合新闻
    {
        "name": "BBC中文",
        "url": "https://feeds.bbci.co.uk/zhongwen/simp/rss.xml",
        "category": "world",
        "language": "zh",
        "description": "BBC中文网新闻",
        "priority": 8
    },
    {
        "name": "纽约时报中文",
        "url": "https://cn.nytimes.com/rss/",
        "category": "world",
        "language": "zh",
        "description": "纽约时报中文版",
        "priority": 8
    },
]


class NewsBriefingService:
    """新闻简报服务"""

    @staticmethod
    async def init_rss_sources(session: AsyncSession) -> int:
        """初始化RSS订阅源"""
        result = await session.execute(select(func.count(RssSource.id)))
        count = result.scalar()

        if count > 0:
            log.info(f"已存在 {count} 个RSS订阅源，跳过初始化")
            return count

        log.info("正在初始化默认RSS订阅源...")
        for source_data in DEFAULT_RSS_SOURCES:
            source = RssSource(**source_data)
            session.add(source)

        await session.commit()
        log.success(f"成功添加 {len(DEFAULT_RSS_SOURCES)} 个默认RSS订阅源")
        return len(DEFAULT_RSS_SOURCES)

    @staticmethod
    async def fetch_rss_feed(url: str, timeout: int = 30) -> list[dict]:
        """从RSS源获取文章列表"""
        articles = []
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                response = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                response.raise_for_status()

            feed = feedparser.parse(response.text)

            for entry in feed.entries:
                article = {
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "summary": entry.get("summary", entry.get("description", "")),
                    "content": "",
                    "published": None,
                }

                # 尝试获取完整内容
                if "content" in entry:
                    article["content"] = entry.content[0].get("value", "")
                elif "summary_detail" in entry:
                    article["content"] = entry.summary_detail.get("value", "")

                # 解析发布时间
                if "published_parsed" in entry and entry.published_parsed:
                    article["published"] = datetime(*entry.published_parsed[:6])
                elif "updated_parsed" in entry and entry.updated_parsed:
                    article["published"] = datetime(*entry.updated_parsed[:6])

                articles.append(article)

        except Exception as e:
            log.error(f"获取RSS源失败 {url}: {e}")

        return articles

    @staticmethod
    def generate_article_uuid(link: str, title: str) -> str:
        """根据链接和标题生成唯一标识"""
        content = f"{link}:{title}"
        return hashlib.md5(content.encode()).hexdigest()

    @staticmethod
    async def save_articles_to_doc(session: AsyncSession, articles: list[dict], source: RssSource) -> int:
        """将文章保存到sys_doc表"""
        saved_count = 0

        for article in articles:
            if not article["title"] or not article["link"]:
                continue

            # 检查是否已存在
            result = await session.execute(
                select(SysDoc).where(SysDoc.source == article["link"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                continue

            # 创建新文档
            content = article["content"] or article["summary"] or ""
            doc = SysDoc(
                title=article["title"][:500] if article["title"] else "",
                name=article["title"][:500] if article["title"] else "",
                type="rss_article",
                content=content,
                desc=article["summary"][:1000] if article["summary"] else "",
                source=article["link"],
                doc_time=article["published"] or timezone.now(),
                status=1,
                created_by=1,
                created_user="admin",
            )

            session.add(doc)
            saved_count += 1

        if saved_count > 0:
            await session.commit()

        return saved_count

    @staticmethod
    async def fetch_all_sources(session: AsyncSession) -> int:
        """从所有活跃的RSS源抓取文章"""
        result = await session.execute(
            select(RssSource).where(RssSource.is_active == True).order_by(RssSource.priority.desc())
        )
        sources = result.scalars().all()

        total_saved = 0

        for source in sources:
            log.info(f"正在抓取: {source.name} ({source.url})")

            try:
                articles = await NewsBriefingService.fetch_rss_feed(source.url)
                saved = await NewsBriefingService.save_articles_to_doc(session, articles, source)
                total_saved += saved

                # 更新最后抓取时间
                source.last_fetch_time = timezone.now().isoformat()
                source.error_count = 0

                log.info(f"  - 获取 {len(articles)} 篇文章, 新增 {saved} 篇")

            except Exception as e:
                source.error_count += 1
                log.error(f"  - 抓取失败: {e}")

            await session.commit()

            # 避免请求过快
            await asyncio.sleep(1)

        return total_saved

    @staticmethod
    async def generate_briefing(session: AsyncSession, hours: int = 24) -> Briefing | None:
        """使用AI生成每日简报"""
        # 获取指定时间内的文章
        since_time = timezone.now() - timedelta(hours=hours)

        result = await session.execute(
            select(SysDoc)
            .where(SysDoc.type == "rss_article")
            .where(SysDoc.created_time >= since_time)
            .order_by(SysDoc.created_time.desc())
            .limit(50)
        )
        docs = result.scalars().all()

        if not docs:
            log.warning("没有找到最近的新闻文章")
            return None

        log.info(f"找到 {len(docs)} 篇最近文章，正在生成简报...")

        # 构建文章摘要
        articles_text = []
        doc_ids = []

        for i, doc in enumerate(docs, 1):
            doc_ids.append(doc.id)
            article_info = f"""
【文章{i}】
标题: {doc.title}
摘要: {doc.desc[:300] if doc.desc else '无'}
来源: {doc.source}
时间: {doc.doc_time}
"""
            articles_text.append(article_info)

        articles_content = "\n".join(articles_text)

        # 创建简报记录
        today = timezone.now().date()
        briefing = Briefing(
            title=f"{today.strftime('%Y年%m月%d日')} 每日新闻简报",
            date=today,
            source_count=len(docs),
            doc_ids=doc_ids,
            status=0,  # 生成中
        )
        session.add(briefing)
        await session.commit()

        # 构建提示词
        system_prompt = """你是一位专业的新闻分析师和简报编辑。你的任务是：
1. 分析提供的新闻文章
2. 提取关键信息和重要趋势
3. 生成结构化的每日简报

输出格式要求：
- 使用Markdown格式
- 包含以下部分：
  - **今日要闻概览**：3-5个最重要的新闻要点
  - **科技动态**：科技领域重要新闻
  - **财经资讯**：财经相关新闻（如有）
  - **深度分析**：对重要趋势的分析洞察
  - **值得关注**：未来可能的发展方向

请确保：
- 信息准确，引用原文
- 语言简洁专业
- 突出重点，避免冗余
"""

        user_prompt = f"""请根据以下{len(docs)}篇新闻文章，生成今日({today.strftime('%Y年%m月%d日')})的新闻简报：

{articles_content}

请生成一份全面、有洞察力的每日新闻简报。"""

        try:
            # 调用LLM生成简报
            response = await llm_service.get_llm_response(system_prompt, user_prompt)

            # 更新简报内容
            briefing.content = response
            briefing.status = 1  # 已完成
            briefing.generation_time = timezone.now()
            briefing.model_used = "default"

            # 提取关键要点
            key_points = []
            if "要闻" in response or "要点" in response:
                lines = response.split("\n")
                for line in lines:
                    if line.strip().startswith(("-", "*", "•", "1", "2", "3", "4", "5")):
                        point = line.strip().lstrip("-*•0123456789. ")
                        if len(point) > 10:
                            key_points.append(point[:200])
                            if len(key_points) >= 5:
                                break

            briefing.key_points = key_points if key_points else None
            briefing.summary = response[:500] if response else None

            await session.commit()
            log.success(f"简报生成成功: {briefing.title}")

            return briefing

        except Exception as e:
            briefing.status = 2  # 失败
            briefing.error_msg = str(e)
            await session.commit()
            log.error(f"简报生成失败: {e}")
            return None

    @staticmethod
    async def run_daily_briefing() -> Briefing | None:
        """执行每日简报任务（供定时任务调用）"""
        log.info("=" * 50)
        log.info("开始执行每日新闻简报任务")
        log.info("=" * 50)

        async with async_db_session() as session:
            # 1. 初始化RSS订阅源
            log.info("[步骤1] 检查并初始化RSS订阅源")
            await NewsBriefingService.init_rss_sources(session)

            # 2. 从RSS源抓取文章
            log.info("[步骤2] 从RSS源抓取文章")
            total_articles = await NewsBriefingService.fetch_all_sources(session)
            log.info(f"共新增 {total_articles} 篇文章")

            # 3. 生成每日简报
            log.info("[步骤3] 使用AI生成每日简报")
            briefing = await NewsBriefingService.generate_briefing(session)

            if briefing and briefing.status == 1:
                log.info("=" * 50)
                log.info("简报生成完成!")
                log.info(f"标题: {briefing.title}")
                log.info(f"引用文章数: {briefing.source_count}")
                log.info("=" * 50)
            else:
                log.warning("简报生成失败或无内容")

            return briefing


news_briefing_service = NewsBriefingService()
