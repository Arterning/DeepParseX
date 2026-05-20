#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import re

from backend.app.admin.schema.unified_search_schema import IntentScores
from backend.app.admin.service.ai_service import call_llm
from backend.common.log import log

_SYSTEM_PROMPT = (
    '你是一个查询意图分类器。分析用户问题，判断它适合哪些检索方式，返回各方式的置信分（0~1之间的小数）。\n\n'
    '检索方式说明：\n'
    '- fulltext（全文检索）：用户想搜索包含特定关键词的文档或文件\n'
    '- rag（知识问答）：用户想获取文档中的知识、理解某个概念、分析某个主题\n'
    '- text_to_sql（数据查询）：用户想查询结构化数据，如统计数量、查看记录列表、汇总数据\n'
    '- graph（图谱问答）：用户想了解实体之间的关系、找到关联实体\n\n'
    '只返回JSON对象，不要有任何其他内容，例如：\n'
    '{"fulltext": 0.2, "rag": 0.8, "text_to_sql": 0.1, "graph": 0.3}'
)

# 关键词规则兜底，LLM 失败时使用
_SQL_KEYWORDS = re.compile(r'统计|数量|查询|查一下|列出|多少|汇总|排行|top|count|sum', re.IGNORECASE)
_RAG_KEYWORDS = re.compile(r'是什么|介绍|解释|说明|分析|总结|什么意思|怎么|为什么|原因|内容')
_FT_KEYWORDS = re.compile(r'搜索|找一下|找找|包含|关键词|相关文件|相关文档')
_GRAPH_KEYWORDS = re.compile(r'关系|相关联|上下游|关联|连接|组织架构|谁认识')


async def detect_intent(question: str) -> IntentScores:
    try:
        raw = await call_llm(
            question,
            _SYSTEM_PROMPT,
            {"llm": {"temperature": 0, "max_tokens": 100}},
        )
        raw = raw.strip()
        # 提取 JSON（LLM 有时会加 ```json 包裹）
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            data = json.loads(m.group())
            return IntentScores(
                fulltext=float(data.get("fulltext", 0)),
                rag=float(data.get("rag", 0)),
                text_to_sql=float(data.get("text_to_sql", 0)),
                graph=float(data.get("graph", 0)),
            )
    except Exception as e:
        log.warning(f"[intent] LLM 分类失败，降级到规则: {repr(e)}")

    # 规则兜底
    return IntentScores(
        fulltext=0.7 if _FT_KEYWORDS.search(question) else 0.1,
        rag=0.7 if _RAG_KEYWORDS.search(question) else 0.2,
        text_to_sql=0.8 if _SQL_KEYWORDS.search(question) else 0.1,
        graph=0.6 if _GRAPH_KEYWORDS.search(question) else 0.0,
    )
