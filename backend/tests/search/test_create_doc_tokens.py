#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 create_doc_tokens 方法（需要数据库连接）
"""

import sys
import asyncio

sys.path.append('../')

from backend.app.admin.service.doc_service import sys_doc_service


async def test_create_doc_tokens():
    """测试创建文档分词"""
    print("=" * 50)
    print("测试 create_doc_tokens 方法 (需要数据库连接)")
    print("=" * 50)

    # 需要提供一个存在的文档ID
    test_doc_id = 1  # 根据实际情况修改

    try:
        print(f"\n为文档 ID={test_doc_id} 创建分词...")
        result = await sys_doc_service.create_doc_tokens(id=test_doc_id)
        print(f"  结果: {result}")
    except Exception as e:
        print(f"  出错: {e}")


if __name__ == '__main__':
    asyncio.run(test_create_doc_tokens())