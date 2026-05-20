#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查询改写服务

将用户的自然语言问题改写为更适合检索的关键词形式。
用户提问往往带有疑问句结构和无关修饰词，直接做分词/向量检索效果差；
改写后提取核心检索词，显著提升召回率。
"""
import re

from backend.app.admin.service.ai_service import call_llm
from backend.common.log import log

_REWRITE_SYSTEM_PROMPT = (
    '你是一个搜索查询优化器。将用户的自然语言问题改写为适合全文检索和语义检索的简短查询词。\n\n'
    '改写规则：\n'
    '1. 提取核心实体、关键词，去掉疑问词（"是什么"、"怎么"、"为什么"等）和时间修饰词（"最近"、"近期"等）\n'
    '2. 保留最关键的名词和动词，用空格分隔\n'
    '3. 如果问题中有人名/地名/机构名，务必保留\n'
    '4. 输出长度控制在 2~8 个词，不要输出完整句子\n'
    '5. 只返回改写后的查询词，不要有任何解释\n\n'
    '示例：\n'
    '用户: "张三这个人最近有什么活动？" → 张三 活动\n'
    '用户: "公司去年的财务报告内容是什么？" → 财务报告\n'
    '用户: "介绍一下区块链技术的原理" → 区块链 技术 原理\n'
    '用户: "XXX项目的风险评估报告" → XXX项目 风险评估\n'
)

# 去掉常见疑问/修饰结构的正则，作为 LLM 失败时的兜底
_FILLER_RE = re.compile(
    r'(请问|请|帮我|帮忙|你知道|我想知道|能告诉我|查一下|找一下|搜一下'
    r'|是什么|是啥|有哪些|有什么|怎么样|怎样|如何|为什么|为何'
    r'|最近|近期|近来|当前|目前|现在|这个|这些|那个|那些'
    r'|吗|呢|啊|哦|嗯|\?|？|。|，|,|\.)+',
    re.IGNORECASE,
)


async def rewrite_query(question: str) -> str:
    """
    将自然语言问题改写为检索友好的关键词串。
    失败时降级返回规则清洗后的原始问题。
    """
    try:
        result = await call_llm(
            question,
            _REWRITE_SYSTEM_PROMPT,
            {'llm': {'temperature': 0, 'max_tokens': 60}},
        )
        rewritten = result.strip().splitlines()[0].strip()
        if rewritten and len(rewritten) <= 100:
            log.debug(f'[query_rewrite] "{question}" → "{rewritten}"')
            return rewritten
    except Exception as e:
        log.warning(f'[query_rewrite] LLM 改写失败，降级到规则清洗: {repr(e)}')

    # 规则兜底：去掉疑问/修饰词后返回剩余内容
    cleaned = _FILLER_RE.sub(' ', question).strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned if cleaned else question
