#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ruff: noqa: I001
"""
邮件文档知识图谱构建脚本

读取所有类型为"邮件"的文档，调用 build_graph 方法构建知识图谱
"""
import logging
import sys
import asyncio
from typing import List

from anyio import run

sys.path.append('../')

from sqlalchemy import select, distinct
from backend.database.db_pg import async_db_session
from backend.app.admin.model import SysDoc
from backend.app.admin.model import SubjectPredictObject
from backend.app.admin.service.doc_service import sys_doc_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def get_email_docs() -> List[SysDoc]:
    """获取所有类型为'邮件'的文档"""
    async with async_db_session() as db:
        stmt = select(SysDoc).where(SysDoc.type == 'email')
        result = await db.execute(stmt)
        docs = result.scalars().all()
        return list(docs)


async def get_processed_doc_ids() -> set:
    """获取已经提取过知识图谱的文档ID"""
    async with async_db_session() as db:
        stmt = select(distinct(SubjectPredictObject.doc_id)).where(
            SubjectPredictObject.doc_id.isnot(None)
        )
        result = await db.execute(stmt)
        doc_ids = result.scalars().all()
        return set(doc_ids)


async def build_email_graphs(
    entity_types: List[str] = None,
    batch_size: int = 10,
    skip_ids: List[int] = None,
    skip_processed: bool = True
) -> None:
    """
    为所有邮件文档构建知识图谱

    Args:
        entity_types: 需要提取的实体类型列表，如 ['人物', '组织', '地点']
        batch_size: 每批处理的文档数量
        skip_ids: 需要跳过的文档ID列表
        skip_processed: 是否跳过已经提取过知识图谱的文档
    """
    skip_ids = set(skip_ids or [])

    # 获取已处理过的文档ID
    if skip_processed:
        logger.info('正在获取已处理过的文档ID...')
        processed_ids = await get_processed_doc_ids()
        logger.info(f'已有 {len(processed_ids)} 个文档提取过知识图谱，将跳过这些文档')
        skip_ids = skip_ids | processed_ids

    logger.info('开始获取邮件文档...')
    docs = await get_email_docs()
    total_emails = len(docs)

    # 过滤掉需要跳过的文档
    docs = [doc for doc in docs if doc.id not in skip_ids]
    logger.info(f'共有 {total_emails} 个邮件文档，跳过 {total_emails - len(docs)} 个已处理的文档')

    total = len(docs)
    logger.info(f'共找到 {total} 个邮件文档需要处理')

    if total == 0:
        logger.info('没有需要处理的邮件文档')
        return

    success_count = 0
    fail_count = 0
    failed_ids = []

    for i, doc in enumerate(docs, 1):
        logger.info(f'[{i}/{total}] 正在处理文档: id={doc.id}, title={doc.title[:50] if doc.title else "无标题"}...')

        try:
            spo_list = await sys_doc_service.build_graph(pk=doc.id, entity_types=entity_types)
            spo_count = len(spo_list) if spo_list else 0
            logger.info(f'[{i}/{total}] 文档 {doc.id} 处理完成，提取了 {spo_count} 个三元组')
            success_count += 1
        except Exception as e:
            logger.error(f'[{i}/{total}] 文档 {doc.id} 处理失败: {str(e)}')
            fail_count += 1
            failed_ids.append(doc.id)

        # 每处理一批文档，暂停一下避免资源占用过高
        if i % batch_size == 0:
            logger.info(f'已处理 {i}/{total} 个文档，暂停1秒...')
            await asyncio.sleep(1)

    logger.info('=' * 50)
    logger.info(f'处理完成! 成功: {success_count}, 失败: {fail_count}')
    if failed_ids:
        logger.info(f'失败的文档ID: {failed_ids}')


async def main() -> None:
    """主函数"""
    logger.info('邮件知识图谱构建脚本启动')

    # 可以根据需要配置实体类型
    # 例如: entity_types = ['人物', '组织', '地点', '时间', '事件']
    entity_types = None  # None 表示使用默认配置

    await build_email_graphs(
        entity_types=entity_types,
        batch_size=10,
        skip_ids=[],  # 可以在这里添加需要跳过的文档ID
        skip_processed=True  # 自动跳过已经提取过知识图谱的文档
    )

    logger.info('脚本执行完毕')


if __name__ == '__main__':
    run(main)
