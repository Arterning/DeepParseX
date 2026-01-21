#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ruff: noqa: I001
"""
文档向量计算脚本

读取所有文档，调用 compute_embedding 方法进行向量计算
自动跳过已经计算过向量的文档
"""
import logging
import sys
import asyncio
from typing import List, Set

from anyio import run

sys.path.append('../')

from sqlalchemy import select, distinct
from backend.database.db_pg import async_db_session
from backend.app.admin.model import SysDoc
from backend.app.admin.model.sys_doc_embedding import SysDocEmbedding
from backend.app.admin.service.doc_service import sys_doc_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def get_all_docs() -> List[SysDoc]:
    """获取所有文档"""
    async with async_db_session() as db:
        stmt = select(SysDoc).where(SysDoc.content.isnot(None))
        result = await db.execute(stmt)
        docs = result.scalars().all()
        return list(docs)


async def get_processed_doc_ids() -> Set[int]:
    """获取已经计算过向量的文档ID"""
    async with async_db_session() as db:
        stmt = select(distinct(SysDocEmbedding.doc_id)).where(
            SysDocEmbedding.doc_id.isnot(None)
        )
        result = await db.execute(stmt)
        doc_ids = result.scalars().all()
        return set(doc_ids)


async def compute_all_embeddings(
    batch_size: int = 10,
    skip_ids: List[int] = None,
    skip_processed: bool = True,
    doc_type: str = None
) -> None:
    """
    为所有文档计算向量

    Args:
        batch_size: 每批处理的文档数量
        skip_ids: 需要跳过的文档ID列表
        skip_processed: 是否跳过已经计算过向量的文档
        doc_type: 指定文档类型，如 '邮件'、'文档' 等，None 表示所有类型
    """
    skip_ids = set(skip_ids or [])

    # 获取已处理过的文档ID
    if skip_processed:
        logger.info('正在获取已计算过向量的文档ID...')
        processed_ids = await get_processed_doc_ids()
        logger.info(f'已有 {len(processed_ids)} 个文档计算过向量，将跳过这些文档')
        skip_ids = skip_ids | processed_ids

    logger.info('开始获取文档列表...')
    docs = await get_all_docs()
    total_docs = len(docs)

    # 按类型过滤
    if doc_type:
        docs = [doc for doc in docs if doc.type == doc_type]
        logger.info(f'筛选类型为 "{doc_type}" 的文档: {len(docs)} 个')

    # 过滤掉需要跳过的文档
    docs = [doc for doc in docs if doc.id not in skip_ids]
    logger.info(f'共有 {total_docs} 个文档，跳过 {total_docs - len(docs)} 个已处理的文档')

    total = len(docs)
    logger.info(f'共找到 {total} 个文档需要计算向量')

    if total == 0:
        logger.info('没有需要处理的文档')
        return

    success_count = 0
    fail_count = 0
    failed_ids = []

    for i, doc in enumerate(docs, 1):
        title = doc.title[:50] if doc.title else '无标题'
        logger.info(f'[{i}/{total}] 正在处理文档: id={doc.id}, title={title}...')

        try:
            await sys_doc_service.compute_embedding(id=doc.id)
            logger.info(f'[{i}/{total}] 文档 {doc.id} 向量计算完成')
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
    logger.info('文档向量计算脚本启动')

    await compute_all_embeddings(
        batch_size=10,
        skip_ids=[],  # 可以在这里添加需要跳过的文档ID
        skip_processed=True,  # 自动跳过已经计算过向量的文档
        doc_type=None  # None 表示处理所有类型，可以指定如 '邮件'
    )

    logger.info('脚本执行完毕')


if __name__ == '__main__':
    run(main)
