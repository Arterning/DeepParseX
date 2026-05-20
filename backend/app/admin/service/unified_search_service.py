#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import time

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin.schema.unified_search_schema import (
    DocChunk,
    IntentScores,
    SourceItem,
    UnifiedSearchResponse,
)
from backend.app.admin.service.ai_service import call_llm
from backend.app.admin.service.embedding_service import embed_text_chunks
from backend.app.admin.service.graph_qa_service import query_graph
from backend.app.admin.service.intent_service import detect_intent
from backend.app.admin.service.query_rewrite_service import rewrite_query
from backend.common.log import log

# 意图分数高于此阈值才启用该路径（AI 自动模式下使用）
_INTENT_THRESHOLD = 0.5


# ── D1 全文检索 ───────────────────────────────────────────────────────────────

async def _run_fulltext(question: str) -> SourceItem:
    try:
        from backend.app.admin.service.doc_service import sys_doc_service
        search_query = await rewrite_query(question)
        log.info(f"[unified/fulltext] 原始问题={question!r} 改写查询={search_query!r}")
        results = await sys_doc_service.search_fulltext_chunks(keyword=search_query, limit=8)
        chunks = [
            DocChunk(
                doc_id=r.doc_id,
                doc_name=r.doc_name,
                content_preview=(r.chunk_text or "")[:300],
            )
            for r in results
        ]
        return SourceItem(type="fulltext", chunks=chunks)
    except Exception as e:
        log.error(f"[unified] 全文检索失败: {repr(e)}")
        return SourceItem(type="fulltext", chunks=[], sql_error=repr(e))


# ── D2 RAG 问答 ───────────────────────────────────────────────────────────────

async def _run_rag(question: str) -> SourceItem:
    try:
        from backend.app.admin.service.doc_service import sys_doc_service
        from backend.app.admin.service.chat_service import _rrf_fusion

        search_query = await rewrite_query(question)
        log.info(f"[unified/rag] 原始问题={question!r} 改写查询={search_query!r}")
        emb = (await embed_text_chunks(search_query))[0]["embs"]
        vector_results, fulltext_results = await asyncio.gather(
            sys_doc_service.search_similar_docs(
                query_vector=emb, limit=10, distance_threshold=1.2
            ),
            sys_doc_service.search_fulltext_chunks(keyword=search_query, limit=10),
        )
        merged = _rrf_fusion(vector_results, fulltext_results)[:5]

        # 去重构建 context
        context_parts = []
        chunks = []
        for i, item in enumerate(merged, 1):
            text = (item.get("chunk_text") or "")
            preview = text[:300] + ("..." if len(text) > 300 else "")
            chunks.append(DocChunk(
                doc_id=item.get("doc_id"),
                doc_name=item.get("doc_name"),
                content_preview=preview,
            ))
            context_parts.append(f"[{i}] 来源：{item.get('doc_name', '未知')}\n{text[:500]}")

        context = "\n\n".join(context_parts)
        if not context:
            return SourceItem(type="rag", chunks=[], path_answer="知识库中未找到相关内容。")

        system_prompt = (
            "你是一个知识问答助手。根据以下文档内容回答用户问题，用简洁清晰的中文作答，"
            "可以用 [1][2] 标注来源编号。\n\n"
            f"## 参考文档\n{context}"
        )
        answer = await call_llm(
            question, system_prompt, {"llm": {"temperature": 0.3, "max_tokens": 800}}
        )
        return SourceItem(type="rag", chunks=chunks, path_answer=answer.strip())
    except Exception as e:
        log.error(f"[unified] RAG 失败: {repr(e)}")
        return SourceItem(type="rag", chunks=[], sql_error=repr(e))


# ── D3 Text-to-SQL ────────────────────────────────────────────────────────────

async def _run_text2sql(question: str, user_id: int, db: AsyncSession) -> SourceItem:
    try:
        from backend.app.admin.service.text2sql_service import (
            _retrieve_schema,
            _retrieve_examples,
            _generate_sql,
            _validate_sql,
            _execute_readonly,
            _fix_sql,
            _build_schema_context,
            _build_few_shot_context,
        )

        tables = await _retrieve_schema(db, question)
        if not tables:
            return SourceItem(type="text_to_sql", sql_error="没有找到可查询的数据表")

        allowed = {t.table_name.lower() for t in tables if t.table_name}
        schema_ctx = _build_schema_context(tables)
        examples = await _retrieve_examples(db, question)
        few_shot_ctx = _build_few_shot_context(examples)

        sql = await _generate_sql(question, schema_ctx, few_shot_ctx)

        for attempt in range(3):
            ok, err = _validate_sql(sql, allowed)
            if not ok:
                if attempt < 2:
                    sql = await _fix_sql(question, sql, err, schema_ctx)
                    continue
                return SourceItem(type="text_to_sql", sql=sql, sql_error=err)
            try:
                columns, rows, _ = await _execute_readonly(sql)
                rows_ser = [
                    [str(v) if not isinstance(v, (int, float, bool, type(None), str)) else v for v in row]
                    for row in rows
                ]
                return SourceItem(
                    type="text_to_sql",
                    sql=sql,
                    columns=columns,
                    rows=rows_ser,
                    row_count=len(rows_ser),
                )
            except asyncio.TimeoutError:
                return SourceItem(type="text_to_sql", sql=sql, sql_error="查询超时")
            except Exception as e:
                if attempt < 2:
                    sql = await _fix_sql(question, sql, repr(e), schema_ctx)
                else:
                    return SourceItem(type="text_to_sql", sql=sql, sql_error=repr(e))

        return SourceItem(type="text_to_sql", sql_error="生成SQL失败")
    except Exception as e:
        log.error(f"[unified] Text-to-SQL 失败: {repr(e)}")
        return SourceItem(type="text_to_sql", sql_error=repr(e))


# ── D5 融合答案 ───────────────────────────────────────────────────────────────

async def _fuse_and_answer(question: str, sources: list[SourceItem]) -> str:
    parts = []
    for src in sources:
        if src.type == "rag" and src.path_answer:
            parts.append(f"【知识问答】\n{src.path_answer}")
        elif src.type == "fulltext" and src.chunks:
            snippets = "\n".join(
                f"- {c.doc_name}: {c.content_preview}" for c in src.chunks[:3]
            )
            parts.append(f"【全文检索】找到以下相关文档：\n{snippets}")
        elif src.type == "text_to_sql" and src.columns and src.rows is not None:
            preview_rows = src.rows[:5]
            table_text = "\t".join(src.columns or []) + "\n"
            for row in preview_rows:
                table_text += "\t".join(str(v) for v in row) + "\n"
            parts.append(f"【数据查询】返回 {src.row_count} 条记录：\n{table_text}")
        elif src.type == "graph" and src.path_answer:
            parts.append(f"【图谱问答】\n{src.path_answer}")

    if not parts:
        return "未找到相关内容。"

    context = "\n\n".join(parts)
    system_prompt = (
        "你是一个智能问答助手。以下是来自多个检索路径的结果，"
        "请综合这些信息，用简洁清晰的中文给出统一答案。\n\n"
        f"## 检索结果\n{context}"
    )
    try:
        answer = await call_llm(
            question, system_prompt, {"llm": {"temperature": 0.3, "max_tokens": 600}}
        )
        return answer.strip()
    except Exception as e:
        log.error(f"[unified] 融合答案生成失败: {repr(e)}")
        return context  # 降级：直接拼接各路径结果


# ── 公开入口 ──────────────────────────────────────────────────────────────────

class UnifiedSearchService:

    async def query(
        self,
        question: str,
        enabled_paths: list[str] | None,
        user_id: int,
        db: AsyncSession,
    ) -> UnifiedSearchResponse:
        start_ms = int(time.time() * 1000)

        # 1. 意图识别
        intent = await detect_intent(question)

        # 2. 确定执行路径
        if enabled_paths is not None:
            # 用户手动指定
            paths_to_run = [p for p in enabled_paths if p in ("fulltext", "rag", "text_to_sql", "graph")]
        else:
            # AI 自动选择
            paths_to_run = [
                p for p, score in [
                    ("fulltext", intent.fulltext),
                    ("rag", intent.rag),
                    ("text_to_sql", intent.text_to_sql),
                    ("graph", intent.graph),
                ]
                if score >= _INTENT_THRESHOLD
            ]
            # 至少执行一条路径（选得分最高的）
            if not paths_to_run:
                top = max(
                    [("fulltext", intent.fulltext), ("rag", intent.rag),
                     ("text_to_sql", intent.text_to_sql), ("graph", intent.graph)],
                    key=lambda x: x[1],
                )
                paths_to_run = [top[0]]

        # 3. 并行执行各路径
        tasks = {}
        if "fulltext" in paths_to_run:
            tasks["fulltext"] = _run_fulltext(question)
        if "rag" in paths_to_run:
            tasks["rag"] = _run_rag(question)
        if "text_to_sql" in paths_to_run:
            tasks["text_to_sql"] = _run_text2sql(question, user_id, db)
        if "graph" in paths_to_run:
            tasks["graph"] = query_graph(question, db)

        if tasks:
            results_list = await asyncio.gather(*tasks.values(), return_exceptions=True)
            sources: list[SourceItem] = []
            for key, result in zip(tasks.keys(), results_list):
                if isinstance(result, Exception):
                    log.error(f"[unified] 路径 {key} 异常: {repr(result)}")
                    sources.append(SourceItem(type=key, sql_error=repr(result)))
                else:
                    sources.append(result)
        else:
            sources = []

        # 4. 融合答案
        answer = await _fuse_and_answer(question, sources)

        elapsed = int(time.time() * 1000) - start_ms
        return UnifiedSearchResponse(
            answer=answer,
            intent=intent,
            used_paths=paths_to_run,
            sources=sources,
            execution_time_ms=elapsed,
        )


unified_search_service = UnifiedSearchService()
