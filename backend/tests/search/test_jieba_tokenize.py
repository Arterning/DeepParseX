#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 jieba 分词功能
"""

import sys
sys.path.append('../')

import jieba


def test_jieba_tokenize():
    """测试jieba分词"""
    print("=" * 50)
    print("测试 jieba 分词")
    print("=" * 50)

    test_cases = [
        "日本东京",
        "中华人民共和国",
        "人工智能技术发展",
        "毒狗案件",
    ]

    for text in test_cases:
        # cut 精确模式
        cut_result = list(jieba.cut(text))
        # cut_for_search 搜索引擎模式
        search_result = list(jieba.cut_for_search(text))

        print(f"\n原文: {text}")
        print(f"  jieba.cut: {cut_result}")
        print(f"  jieba.cut_for_search: {search_result}")


def test_jieba_tokenize_with_position():
    """测试 jieba.tokenize 获取位置信息"""
    print("\n" + "=" * 50)
    print("测试 jieba.tokenize (带位置信息)")
    print("=" * 50)

    test_cases = [
        "日本东京",
        "中华人民共和国",
        "人工智能技术发展",
    ]

    for text in test_cases:
        # tokenize 返回 (word, start, end)
        tokens = list(jieba.tokenize(text, mode='search'))
        print(f"\n原文: {text}")
        print(f"  分词结果 (word, start, end):")
        for word, start, end in tokens:
            print(f"    '{word}': 位置 {start}-{end}")


if __name__ == '__main__':
    test_jieba_tokenize()
    test_jieba_tokenize_with_position()