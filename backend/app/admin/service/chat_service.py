#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import json
import re
from collections import OrderedDict

from backend.app.admin.schema.chat import ChatParam
from backend.app.admin.service.doc_service import sys_doc_service
from backend.app.admin.service.embedding_service import embed_text_chunks
from backend.app.admin.service.ai_service import ai_service
from backend.app.admin.service.query_rewrite_service import rewrite_query
from backend.database.db_pg import async_db_session
from backend.app.admin.model.sys_chat_message import ChatMessage
from sqlalchemy import select
from backend.common.log import log


def _rrf_fusion(
    vector_results: list,
    fulltext_results: list,
    k: int = 60,
) -> list[dict]:
    """
    Reciprocal Rank Fusion：将向量检索与全文检索的排序结果融合。

    每条结果统一为 dict: {doc_id, doc_name, chunk_text, rrf_score}
    key 使用 (doc_id, chunk_text[:100])，避免不同文件的相同内容跨文件叠加分数。
    """
    scores: dict[tuple, dict] = {}

    def _key(doc_id, chunk_text: str) -> tuple:
        return (doc_id, (chunk_text or "")[:100])

    # 向量结果（已按 distance ASC 排序 → rank 从 0 开始）
    for rank, row in enumerate(vector_results):
        ck = _key(row.doc_id, row.chunk_text)
        if ck not in scores:
            scores[ck] = {
                "doc_id": row.doc_id,
                "doc_name": row.doc_name,
                "chunk_text": row.chunk_text,
                "rrf_score": 0.0,
            }
        scores[ck]["rrf_score"] += 1.0 / (k + rank)

    # 全文结果（已按 ts_rank DESC 排序 → rank 从 0 开始）
    for rank, row in enumerate(fulltext_results):
        ck = _key(row.doc_id, row.chunk_text)
        if ck not in scores:
            scores[ck] = {
                "doc_id": row.doc_id,
                "doc_name": row.doc_name,
                "chunk_text": row.chunk_text,
                "rrf_score": 0.0,
            }
        scores[ck]["rrf_score"] += 1.0 / (k + rank)

    # 按融合分数降序
    merged = sorted(scores.values(), key=lambda x: x["rrf_score"], reverse=True)
    return merged


async def _llm_rerank(
    question: str,
    candidates: list[dict],
    top_n: int = 5,
) -> list[dict]:
    """
    用 LLM 对候选 chunks 做 listwise rerank，返回前 top_n 条。
    如果 LLM 调用失败，降级返回 RRF 排序前 top_n。
    """
    if len(candidates) <= top_n:
        return candidates

    # 构建编号列表供 LLM 排序
    numbered = []
    for i, c in enumerate(candidates):
        preview = (c["chunk_text"] or "")[:300]
        numbered.append(f"[{i}] {preview}")
    chunks_text = "\n".join(numbered)

    prompt = (
        f"用户问题：{question}\n\n"
        f"以下是 {len(candidates)} 条候选文档片段，请根据与用户问题的相关性从高到低排序，"
        f"只返回最相关的 {top_n} 条的编号，用 JSON 数组格式返回，如 [2, 0, 5]。\n"
        f"不要解释，只返回 JSON 数组。\n\n{chunks_text}"
    )

    try:
        resp = await ai_service.call_llm(
            user_prompt=prompt,
            system_prompt="你是一个文档相关性排序助手，只输出 JSON 数组。",
        )
        # 提取 JSON 数组
        match = re.search(r'\[[\d\s,]+\]', resp)
        if not match:
            return candidates[:top_n]

        indices = json.loads(match.group())
        reranked = []
        seen = set()
        for idx in indices:
            if isinstance(idx, int) and 0 <= idx < len(candidates) and idx not in seen:
                reranked.append(candidates[idx])
                seen.add(idx)
            if len(reranked) >= top_n:
                break

        # 补齐（LLM 可能返回不足 top_n 条）
        if len(reranked) < top_n:
            for c in candidates:
                if c not in reranked:
                    reranked.append(c)
                if len(reranked) >= top_n:
                    break

        return reranked
    except Exception as e:
        log.warning(f"[_llm_rerank] LLM rerank 失败，降级使用 RRF 排序: {repr(e)}")
        return candidates[:top_n]


class ChatService:

    @staticmethod
    async def rag_chat(
        obj: ChatParam,
        check_topk: int = 10,
        rerank: bool = True,
        rerank_top_n: int = 10,
    ):
        # 1. 加载历史对话，构建 OpenAI 格式 messages
        messages = []
        # 根据设置决定是否加载历史消息
        if obj.session_id and obj.send_history is not False:
            async with async_db_session() as db:
                result = await db.execute(
                    select(ChatMessage)
                    .where(ChatMessage.session_id == obj.session_id)
                    .order_by(ChatMessage.created_time.asc())
                )
                for msg in result.scalars().all():
                    role = "user" if msg.sender == "user" else "assistant"
                    messages.append({"role": role, "content": msg.content})

        messages.append({"role": "user", "content": obj.question})
        log.debug(f"[rag_chat] question={obj.question!r}, doc_id={obj.doc_id}, session_id={obj.session_id}, history_len={len(messages)-1}")

        agent_mode = obj.agent_mode is True

        # ── Agent 模式：跳过预检索，让 Agent 自行按需搜索 ──
        if agent_mode:
            from backend.app.admin.service.agent.prompts import build_agent_system_prompt
            system_prompt = build_agent_system_prompt()

            response = await ai_service.chat_with_tools(
                messages=messages,
                system_prompt=system_prompt,
            )
            return {"answer": response, "references": []}

        # ── 传统 RAG 模式：预检索 + 上下文注入 ──
        # 2. 问题改写：提取检索关键词，提升召回率
        rewritten = await rewrite_query(obj.question)
        log.debug(f"[rag_chat] rewritten={rewritten!r}")

        # 3. 目录过滤：将 doc_dir_ids 递归展开为 doc_ids
        search_doc_ids: list[int] | None = None
        if obj.doc_dir_ids:
            from backend.app.admin.crud.crud_doc_dir import doc_dir_dao
            async with async_db_session() as db:
                search_doc_ids = await doc_dir_dao.get_all_doc_ids_in_dirs(db, obj.doc_dir_ids)
            log.debug(f"[rag_chat] doc_dir_ids={obj.doc_dir_ids} → {len(search_doc_ids)} 个文档")

        # 4. 混合检索：向量 + 全文并行召回（使用改写后的查询）
        vector_task = sys_doc_service.search_similar_docs(
            query_vector=(await embed_text_chunks(rewritten))[0]["embs"],
            limit=check_topk,
            distance_threshold=1.2,
            doc_id=obj.doc_id,
            doc_ids=search_doc_ids,
        )
        fulltext_task = sys_doc_service.search_fulltext_chunks(
            keyword=rewritten,
            limit=check_topk,
            doc_id=obj.doc_id,
            doc_ids=search_doc_ids,
        )

        vector_results, fulltext_results = await asyncio.gather(
            vector_task, fulltext_task
        )
        log.debug(f"[rag_chat] vector_results={len(vector_results)} 条, fulltext_results={len(fulltext_results)} 条")

        # 5. RRF 融合排序
        merged = _rrf_fusion(vector_results, fulltext_results)
        log.debug(f"[rag_chat] RRF 融合后 {len(merged)} 条")

        # 6. 可选 LLM Rerank
        if rerank and len(merged) > rerank_top_n:
            ranked = await _llm_rerank(obj.question, merged, top_n=rerank_top_n)
        else:
            ranked = merged[:rerank_top_n]
        log.debug(f"[rag_chat] rerank 后 {len(ranked)} 条: {[r['doc_name'] for r in ranked]}")

        # 7. 按文件分组 chunks，合并同一文件的内容
        doc_groups: OrderedDict[int, dict] = OrderedDict()
        for item in ranked:
            if not item["chunk_text"]:
                continue
            did = item["doc_id"]
            if did not in doc_groups:
                doc_groups[did] = {
                    "doc_id": did,
                    "doc_name": item["doc_name"],
                    "chunks": [],
                }
            doc_groups[did]["chunks"].append(item["chunk_text"])

        # 构建带编号的引用列表和上下文
        references = []
        context_parts = []
        ref_map = {}
        for ref_idx, (did, group) in enumerate(doc_groups.items(), start=1):
            merged_text = "\n".join(group["chunks"])
            content_preview = merged_text[:300] + ("..." if len(merged_text) > 300 else "")
            doc_name = group["doc_name"]
            references.append({
                "ref_index": ref_idx,
                "doc_id": group["doc_id"],
                "doc_name": doc_name,
                "content_preview": content_preview,
            })
            ref_map[ref_idx] = doc_name
            clean_text = re.sub(r'\[(\d+)\]', r'(\1)', merged_text)
            context_parts.append(f"[{ref_idx}] 来源：{doc_name}\n内容: {clean_text}")

        context = "\n\n".join(context_parts)

        # 8. 构建 system prompt（传统 RAG 模式）
        if context:
            system_prompt = (
                "你是一个知识库助手。\n\n"
                "## 知识库上下文\n"
                "---\n"
                f"{context}\n"
                "---\n\n"
                "## 回答规则\n"
                "1. 请根据上方检索到的上下文回答用户问题，使用 [1]、[2] 等编号标注来源。\n"
                "2. 如果上下文中没有相关信息，可以结合自身知识回答，但请说明哪些内容来自知识库、哪些来自自身知识。\n"
                "3. 回答要准确、简洁、有条理。\n"
            )
        else:
            system_prompt = (
                "你是一个知识库助手。\n\n"
                "知识库中未检索到与用户问题相关的内容。\n\n"
                "## 回答规则\n"
                "1. 请结合自身知识回答用户问题，并说明知识库中未找到直接相关内容。\n"
                "2. 回答要准确、简洁、有条理。\n"
            )

        # 9. 传统 RAG 模式：基于检索上下文直接回答
        response = await ai_service.call_llm(
            user_prompt=obj.question,
            system_prompt=system_prompt,
        )

        # 8. 后处理：将 [N] 编号替换为 [文件标题]，删除不存在的编号
        log.debug(f"[rag_chat] LLM 原始回答: {response!r}")

        def _replace_ref(m):
            try:
                idx = int(m.group(1))
            except ValueError:
                return m.group(0)
            name = ref_map.get(idx)
            if name:
                log.debug(f"[rag_chat] 替换 [{idx}] -> [{name}]")
                return f"[{name}]"
            # 不在 ref_map 中的编号保留原样，避免误删 [2024] 等非引用数字
            log.debug(f"[rag_chat] 保留 [{idx}]（不在 ref_map 中）")
            return m.group(0)

        if ref_map:
            response = re.sub(r'\[(\d+)\]', _replace_ref, response)

        log.debug(f"[rag_chat] 替换后回答: {response!r}")
        return {"answer": response, "references": references}
    
    @staticmethod
    async def chat_doc(question: str, context: str, doc_id: int = None):
        """
        文档片段对话：基于用户选择的文本片段回答问题
        不需要检索，不需要持久化，直接基于提供的上下文回答
        """
        system_prompt = (
            "你是一个知识百科助手。请基于你所拥有的内部知识储备回答用户的疑问。\n\n"
            "回答信息尽可能简洁易懂，面向小白。\n\n"
            "除非用户指定仅限基于文档内容回答，否则不要限制你的信息来源范围。\n\n"
        )
        user_prompt = f"<question>{question}</question>\n\n<document>{context}</document>"

        response = await ai_service.call_llm(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
        )

        return {"answer": response}

chat_service = ChatService()
