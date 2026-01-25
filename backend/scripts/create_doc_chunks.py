#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ruff: noqa: I001
"""
文档分块和分词向量创建脚本

读取所有文档，调用 create_doc_tokens 方法进行分块和分词向量创建
自动跳过已经创建过分块的文档
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
from backend.app.admin.model.sys_doc_chunk import SysDocChunk
from backend.app.admin.service.doc_service import sys_doc_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def get_all_docs() -> List[SysDoc]:
    """获取所有有内容的文档"""
    async with async_db_session() as db:
        stmt = select(SysDoc).where(SysDoc.content.isnot(None))
        result = await db.execute(stmt)
        docs = result.scalars().all()
        return list(docs)


async def get_chunked_doc_ids() -> Set[int]:
    """获取已经创建过分块的文档ID"""
    async with async_db_session() as db:
        stmt = select(distinct(SysDocChunk.doc_id)).where(
            SysDocChunk.doc_id.isnot(None)
        )
        result = await db.execute(stmt)
        doc_ids = result.scalars().all()
        return set(doc_ids)


async def create_all_doc_chunks(
    batch_size: int = 10,
    skip_ids: List[int] = None,
    skip_chunked: bool = True,
    doc_type: str = None,
    force_recreate: bool = False
) -> None:
    """
    为所有文档创建分块和分词向量

    Args:
        batch_size: 每批处理的文档数量
        skip_ids: 需要跳过的文档ID列表
        skip_chunked: 是否跳过已经创建过分块的文档
        doc_type: 指定文档类型，如 '邮件'、'文档' 等，None 表示所有类型
        force_recreate: 是否强制重新创建（会删除已有分块）
    """
    skip_ids = set(skip_ids or [])

    # 获取已创建过分块的文档ID
    if skip_chunked and not force_recreate:
        logger.info('正在获取已创建过分块的文档ID...')
        chunked_ids = await get_chunked_doc_ids()
        logger.info(f'已有 {len(chunked_ids)} 个文档创建过分块，将跳过这些文档')
        skip_ids = skip_ids | chunked_ids

    logger.info('开始获取文档列表...')
    docs = await get_all_docs()
    total_docs = len(docs)

    # 按类型过滤
    if doc_type:
        docs = [doc for doc in docs if doc.type == doc_type]
        logger.info(f'筛选类型为 "{doc_type}" 的文档: {len(docs)} 个')

    # 过滤掉需要跳过的文档
    if not force_recreate:
        docs = [doc for doc in docs if doc.id not in skip_ids]
        logger.info(f'共有 {total_docs} 个文档，跳过 {total_docs - len(docs)} 个已处理的文档')

    total = len(docs)
    logger.info(f'共找到 {total} 个文档需要创建分块和分词向量')

    if total == 0:
        logger.info('没有需要处理的文档')
        return

    success_count = 0
    fail_count = 0
    failed_ids = []

    for i, doc in enumerate(docs, 1):
        title = doc.title[:50] if doc.title else '无标题'
        content_length = len(doc.content) if doc.content else 0

        logger.info(f'[{i}/{total}] 正在处理文档: id={doc.id}, title={title}, content_length={content_length}')

        try:
            if force_recreate:
                logger.info(f'[{i}/{total}] 强制重新创建模式，将删除旧分块')

            await sys_doc_service.create_doc_tokens(id=doc.id)

            # 查询创建的分块数量
            async with async_db_session() as db:
                stmt = select(SysDocChunk).where(SysDocChunk.doc_id == doc.id)
                result = await db.execute(stmt)
                chunks = result.scalars().all()
                chunk_count = len(chunks)

            logger.info(f'[{i}/{total}] 文档 {doc.id} 分块创建完成，共 {chunk_count} 个分块')
            success_count += 1
        except Exception as e:
            logger.error(f'[{i}/{total}] 文档 {doc.id} 处理失败: {str(e)}')
            import traceback
            logger.error(traceback.format_exc())
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


async def recreate_doc_chunks_by_ids(doc_ids: List[int]) -> None:
    """
    为指定ID的文档重新创建分块和分词向量

    Args:
        doc_ids: 需要重新创建的文档ID列表
    """
    logger.info(f'开始为 {len(doc_ids)} 个指定文档重新创建分块和分词向量')

    success_count = 0
    fail_count = 0
    failed_ids = []

    for i, doc_id in enumerate(doc_ids, 1):
        logger.info(f'[{i}/{len(doc_ids)}] 正在处理文档ID: {doc_id}')

        try:
            await sys_doc_service.create_doc_tokens(id=doc_id)

            # 查询创建的分块数量
            async with async_db_session() as db:
                stmt = select(SysDocChunk).where(SysDocChunk.doc_id == doc_id)
                result = await db.execute(stmt)
                chunks = result.scalars().all()
                chunk_count = len(chunks)

            logger.info(f'[{i}/{len(doc_ids)}] 文档 {doc_id} 分块创建完成，共 {chunk_count} 个分块')
            success_count += 1
        except Exception as e:
            logger.error(f'[{i}/{len(doc_ids)}] 文档 {doc_id} 处理失败: {str(e)}')
            import traceback
            logger.error(traceback.format_exc())
            fail_count += 1
            failed_ids.append(doc_id)

    logger.info('=' * 50)
    logger.info(f'处理完成! 成功: {success_count}, 失败: {fail_count}')
    if failed_ids:
        logger.info(f'失败的文档ID: {failed_ids}')


async def main() -> None:
    """主函数"""
    logger.info('文档分块和分词向量创建脚本启动')

    # 模式1: 为所有文档创建分块（跳过已有分块的文档）
    await create_all_doc_chunks(
        batch_size=10,
        skip_ids=[],  # 可以在这里添加需要跳过的文档ID
        skip_chunked=True,  # 自动跳过已经创建过分块的文档
        doc_type=None,  # None 表示处理所有类型，可以指定如 '邮件'、'文本' 等
        force_recreate=False  # 设为 True 会强制重新创建所有分块
    )

    # 模式2: 为指定ID的文档重新创建分块（取消注释以使用）
    # await recreate_doc_chunks_by_ids([1, 2, 3])

    logger.info('脚本执行完毕')


if __name__ == '__main__':
    run(main)
