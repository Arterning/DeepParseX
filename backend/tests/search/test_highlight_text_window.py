#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 highlight_text_window 方法
"""

import sys
sys.path.append('../')

from backend.app.admin.service.doc_service import SysDocService


def test_highlight_text_window():
    """测试高亮方法"""
    print("=" * 50)
    print("测试 highlight_text_window 方法")
    print("=" * 50)

    # 测试用例 1: 正常高亮
    text = "日本是一个岛国，日本的首都是东京，日本人口约1.26亿。"
    keywords = ["日本", "东京"]
    result = SysDocService.highlight_text_window(text, keywords)
    print(f"\n测试1 - 正常高亮:")
    print(f"  原文: {text}")
    print(f"  关键词: {keywords}")
    print(f"  结果: {result}")

    # 测试用例 2: content 为 None
    result_none = SysDocService.highlight_text_window(None, ["test"])
    print(f"\n测试2 - content为None:")
    print(f"  结果: '{result_none}' (应为空字符串)")
    assert result_none == '', "content为None时应返回空字符串"

    # 测试用例 3: keywords 为空
    result_empty_kw = SysDocService.highlight_text_window("测试文本", [])
    print(f"\n测试3 - keywords为空:")
    print(f"  结果: '{result_empty_kw}' (应返回前200字符)")

    # 测试用例 4: keywords 包含空字符串
    result_empty_str = SysDocService.highlight_text_window("测试日本文本", ["", "日本", ""])
    print(f"\n测试4 - keywords包含空字符串:")
    print(f"  结果: {result_empty_str}")

    # 测试用例 5: 长文本截断
    long_text = "这是一段很长的文本。" * 100 + "关键词在这里" + "更多文本。" * 100
    result_long = SysDocService.highlight_text_window(long_text, ["关键词"])
    print(f"\n测试5 - 长文本高亮:")
    print(f"  原文长度: {len(long_text)}")
    print(f"  结果: {result_long[:100]}...")

    # 测试用例 6: 没有匹配
    result_no_match = SysDocService.highlight_text_window("这是测试文本", ["不存在的词"])
    print(f"\n测试6 - 无匹配:")
    print(f"  结果: {result_no_match} (应返回前200字符)")

    print("\n高亮方法测试完成!")


if __name__ == '__main__':
    test_highlight_text_window()