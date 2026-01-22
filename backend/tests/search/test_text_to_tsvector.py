#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 text_to_tsvector 函数
"""

import sys
sys.path.append('../')

from backend.app.admin.service.doc_service import text_to_tsvector


def test_text_to_tsvector():
    """测试 tsvector 转换函数"""
    print("=" * 50)
    print("测试 text_to_tsvector 函数")
    print("=" * 50)

    # 测试用例 1: 基本转换
    text = "日本东京"
    result = text_to_tsvector(text)
    print(f"\n测试1 - 基本转换:")
    print(f"  原文: {text}")
    print(f"  结果: {result}")

    # 测试用例 2: 重复词
    text2 = "日本是岛国，日本人口多"
    result2 = text_to_tsvector(text2)
    print(f"\n测试2 - 重复词（应有多个位置）:")
    print(f"  原文: {text2}")
    print(f"  结果: {result2}")

    # 测试用例 3: 空文本
    result3 = text_to_tsvector("")
    print(f"\n测试3 - 空文本:")
    print(f"  结果: '{result3}' (应为空字符串)")
    assert result3 == '', "空文本应返回空字符串"

    # 测试用例 4: None
    result4 = text_to_tsvector(None)
    print(f"\n测试4 - None:")
    print(f"  结果: '{result4}' (应为空字符串)")
    assert result4 == '', "None应返回空字符串"

    # 测试用例 5: 包含单引号
    text5 = "It's a test"
    result5 = text_to_tsvector(text5)
    print(f"\n测试5 - 包含单引号:")
    print(f"  原文: {text5}")
    print(f"  结果: {result5}")

    print("\ntsvector 转换测试完成!")


if __name__ == '__main__':
    test_text_to_tsvector()