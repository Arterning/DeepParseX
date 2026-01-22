#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 text_to_weighted_tsvector 函数
"""

import sys
sys.path.append('../')

from backend.app.admin.service.doc_service import text_to_weighted_tsvector


def test_text_to_weighted_tsvector():
    """测试带权重的 tsvector 转换函数"""
    print("=" * 50)
    print("测试 text_to_weighted_tsvector 函数")
    print("=" * 50)

    # 测试用例 1: 标题和内容
    title = "日本新闻"
    content = "东京是日本的首都"
    doc_type = "新闻"
    result = text_to_weighted_tsvector(title, content, doc_type)
    print(f"\n测试1 - 标题和内容带权重:")
    print(f"  标题: {title}")
    print(f"  内容: {content}")
    print(f"  类型: {doc_type}")
    print(f"  结果: {result}")
    # 验证结果包含权重标记
    assert 'A' in result, "结果应包含权重A"
    assert 'B' in result, "结果应包含权重B"

    # 测试用例 2: 只有标题
    result2 = text_to_weighted_tsvector("测试标题", None, None)
    print(f"\n测试2 - 只有标题:")
    print(f"  结果: {result2}")

    # 测试用例 3: 只有内容
    result3 = text_to_weighted_tsvector(None, "测试内容", None)
    print(f"\n测试3 - 只有内容:")
    print(f"  结果: {result3}")

    print("\n带权重的 tsvector 转换测试完成!")


if __name__ == '__main__':
    test_text_to_weighted_tsvector()