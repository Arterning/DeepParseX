#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 search 方法（需要数据库连接）
"""

import sys
import asyncio

sys.path.append('../')

from backend.app.admin.service.doc_service import sys_doc_service


async def test_search():
    """测试搜索方法"""
    print("=" * 50)
    print("测试 search 方法 (需要数据库连接)")
    print("=" * 50)

    test_keywords = ["日本", "毒狗", "文档"]

    for keyword in test_keywords:
        print(f"\n搜索关键词: {keyword}")
        try:
            result = await sys_doc_service.search(keyword=keyword, page=1, size=5)
            print(f"  总数: {result.get('total', 0)}")
            items = result.get('items', [])
            for i, item in enumerate(items[:3]):
                print(f"  [{i+1}] {item.get('title', 'N/A')}")
                print(f"      高亮: {item.get('hit', 'N/A')[:100]}...")
        except Exception as e:
            print(f"  搜索出错: {e}")


async def test_search_and_highlight_consistency():
    """测试搜索和高亮的一致性"""
    print("\n" + "=" * 50)
    print("测试搜索和高亮一致性")
    print("=" * 50)

    keyword = "日本"

    try:
        # 1. 搜索
        result = await sys_doc_service.search(keyword=keyword, page=1, size=5)
        items = result.get('items', [])

        if not items:
            print("没有搜索到结果")
            return

        # 2. 检查高亮是否包含关键词
        for item in items:
            title = item.get('title', '')
            hit = item.get('hit', '')
            content = item.get('content', '')

            # 检查原文是否包含关键词
            has_keyword_in_content = keyword in (content or '')
            has_highlight_in_hit = '<b>' in hit or '<mark>' in hit

            print(f"\n文档: {item.get('name', 'N/A')}")
            print(f"  原文包含'{keyword}': {has_keyword_in_content}")
            print(f"  高亮结果有标签: {has_highlight_in_hit}")

            if has_keyword_in_content and not has_highlight_in_hit:
                print(f"  ⚠️ 警告: 原文包含关键词但高亮结果中没有标签")

    except Exception as e:
        print(f"测试出错: {e}")


async def run_all_tests():
    """运行所有搜索测试"""
    print("\n" + "=" * 50)
    print("以下测试需要数据库连接，如果没有配置数据库会报错")
    print("=" * 50)

    try:
        await test_search()
        await test_search_and_highlight_consistency()
    except Exception as e:
        print(f"\n数据库测试跳过: {e}")


if __name__ == '__main__':
    asyncio.run(run_all_tests())