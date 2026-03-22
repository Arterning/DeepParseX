#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ruff: noqa: I001
"""
抽象实体筛选脚本

调用 EntityService.find_abstract_entities 筛选出名称为泛指抽象名词的实体，
例如：企业、研究、技术、项目、工作 等没有具体指代对象的词语。
仅做筛选展示，不执行删除。

用法：
    uv run backend/tests/entity/find_abstract_entities.py
"""
import asyncio
import json
import logging
import sys

sys.path.append('../')

from anyio import run

from backend.app.admin.service.entity_service import entity_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


async def main() -> None:
    logger.info('开始筛选泛指抽象名词实体...')

    # 可按实体类型过滤，None 表示全部类型
    # 示例：entity_type=['人物', '组织'] 或 entity_type='组织'
    entity_type = None

    results = await entity_service.find_abstract_entities(
        entity_type=entity_type,
        batch_size=50,
    )

    logger.info(f'共筛选出 {len(results)} 个抽象名词实体')

    if results:
        print('\n=== 抽象名词实体列表 ===')
        for item in results:
            print(f"  id={item['id']:6d}  type={item['entity_type'] or '未知':8s}  name={item['name']}")

        print('\n=== JSON 输出 ===')
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print('未发现抽象名词实体。')


if __name__ == '__main__':
    run(main)
