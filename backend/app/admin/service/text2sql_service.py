#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import json
import re
import time
from typing import Any

import sqlglot
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin.crud.crud_text2sql import (
    crud_text2sql_table,
    crud_text2sql_column,
    crud_text2sql_example,
    crud_text2sql_query_log,
)
from backend.app.admin.model.sys_text2sql_column import Text2SQLColumn
from backend.app.admin.model.sys_text2sql_table import Text2SQLTable
from backend.app.admin.model.sys_text2sql_query_log import Text2SQLQueryLog
from backend.app.admin.model.sys_text2sql_example import Text2SQLExample
from backend.app.admin.schema.text2sql_schema import (
    ClarificationOption,
    ClarificationResult,
    QueryResponse,
)
from backend.app.admin.service.ai_service import call_llm
from backend.app.admin.service.embedding_service import embed_texts
from backend.common.log import log
from backend.database.db_pg import async_db_session, async_engine


# ── 内部工具函数 ──────────────────────────────────────────────────────────────

def _build_schema_context(tables: list[Text2SQLTable]) -> str:
    parts = []
    for t in tables:
        header = f"表名: {t.schema_name}.{t.table_name}"
        if t.display_name:
            header += f"（{t.display_name}）"
        if t.description:
            header += f"\n说明: {t.description}"
        col_lines = []
        for c in sorted(t.columns, key=lambda x: x.ordinal_position or 0):
            col_line = f"  - {c.column_name} ({c.data_type or '未知类型'})"
            if c.description:
                col_line += f": {c.description}"
            if c.sample_values:
                col_line += f"，样例值: {c.sample_values}"
            if c.is_sensitive:
                col_line += "【敏感字段】"
            col_lines.append(col_line)
        parts.append(header + "\n字段:\n" + "\n".join(col_lines))
    return "\n\n".join(parts)


def _build_few_shot_context(examples: list) -> str:
    if not examples:
        return "（暂无示例）"
    parts = []
    for ex in examples:
        parts.append(f"问题: {ex.question}\nSQL: {ex.sql}")
    return "\n\n".join(parts)


def _extract_sql(raw: str) -> str:
    raw = raw.strip()
    # 去掉 markdown 代码块
    match = re.search(r'```(?:sql)?\s*([\s\S]+?)```', raw, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # 直接找 SELECT 开头
    match = re.search(r'(SELECT\s+[\s\S]+)', raw, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return raw


def _rrf_merge(
    vector_results: list[Text2SQLTable],
    keyword_results: list[Text2SQLTable],
    k: int = 60,
) -> list[Text2SQLTable]:
    scores: dict[int, float] = {}
    order: dict[int, Text2SQLTable] = {}
    for rank, t in enumerate(vector_results):
        scores[t.id] = scores.get(t.id, 0) + 1.0 / (k + rank)
        order[t.id] = t
    for rank, t in enumerate(keyword_results):
        scores[t.id] = scores.get(t.id, 0) + 1.0 / (k + rank)
        order[t.id] = t
    sorted_ids = sorted(scores.keys(), key=lambda i: scores[i], reverse=True)
    return [order[i] for i in sorted_ids]


# ── 各阶段逻辑 ────────────────────────────────────────────────────────────────

async def _detect_ambiguity(question: str) -> ClarificationResult | None:
    system_prompt = (
        '你是一个SQL查询助手。判断用户问题是否含有时间/范围歧义（如"最近"、"最新"、"近期"、"一段时间"等模糊词）。\n'
        '若有歧义，返回如下JSON（不要包含任何其他文字）：\n'
        '{"has_ambiguity": true, "prompt": "请确认查询的时间范围：", "options": [{"label":"最近7天","value":"最近7天"},{"label":"最近30天","value":"最近30天"},{"label":"最近3个月","value":"最近3个月"},{"label":"今年","value":"今年"}]}\n'
        '若无歧义，返回：\n'
        '{"has_ambiguity": false}'
    )
    try:
        raw = await call_llm(question, system_prompt, {"llm": {"temperature": 0, "max_tokens": 300}})
        data = json.loads(raw.strip())
        if data.get("has_ambiguity"):
            return ClarificationResult(
                prompt=data.get("prompt", "请确认查询范围："),
                options=[ClarificationOption(**o) for o in data.get("options", [])],
            )
    except Exception as e:
        log.warning(f"[text2sql] 歧义检测失败，跳过: {repr(e)}")
    return None


async def _retrieve_schema(db: AsyncSession, question: str, top_k: int = 5) -> list[Text2SQLTable]:
    emb_results = await embed_texts([question])
    q_embedding = emb_results[0]["embs"] if emb_results else None

    vector_results: list[Text2SQLTable] = []
    if q_embedding:
        vector_results = await crud_text2sql_table.vector_search(db, q_embedding, top_k=top_k * 2)

    keywords = [w for w in re.split(r'\s+|[，。？！,?!]', question) if len(w) >= 2]
    keyword_results = await crud_text2sql_table.keyword_search(db, keywords, top_k=top_k * 2)

    merged = _rrf_merge(vector_results, keyword_results)
    if not merged:
        # 回退：返回所有启用的表
        merged = await crud_text2sql_table.get_active_with_columns(db)
    return merged[:top_k]


async def _retrieve_examples(db: AsyncSession, question: str, top_k: int = 3) -> list:
    emb_results = await embed_texts([question])
    q_embedding = emb_results[0]["embs"] if emb_results else None
    if q_embedding:
        return await crud_text2sql_example.vector_search(db, q_embedding, top_k=top_k)
    return []


async def _generate_sql(question: str, schema_context: str, few_shot_context: str) -> str:
    system_prompt = (
        "你是一个数据库查询助手，只能生成 SELECT 语句。\n\n"
        "### 可用数据表\n"
        f"{schema_context}\n\n"
        "### 参考示例\n"
        f"{few_shot_context}\n\n"
        "### 要求\n"
        "- 只输出 SQL，不要任何解释\n"
        "- 禁止使用 INSERT/UPDATE/DELETE/DROP/TRUNCATE\n"
        "- 日期范围用 >= / <= 而非 BETWEEN\n"
        "- 默认加 LIMIT 1000\n"
        "- 字段名和表名使用双引号包裹以避免大小写问题"
    )
    raw = await call_llm(question, system_prompt, {"llm": {"temperature": 0.1, "max_tokens": 1000}})
    return _extract_sql(raw)


async def _fix_sql(question: str, sql: str, error: str, schema_context: str) -> str:
    system_prompt = (
        "你生成的 SQL 执行出错了，请根据错误信息修正它。只输出修正后的 SQL，不要任何解释。\n\n"
        "### 可用表结构\n"
        f"{schema_context}"
    )
    user_prompt = f"原始问题：{question}\n\n出错的 SQL：\n{sql}\n\n错误信息：{error}\n\n修正后的 SQL："
    raw = await call_llm(user_prompt, system_prompt, {"llm": {"temperature": 0.1, "max_tokens": 1000}})
    return _extract_sql(raw)


def _validate_sql(sql: str, allowed_table_names: set[str]) -> tuple[bool, str]:
    """返回 (is_ok, error_message)"""
    try:
        parsed = sqlglot.parse_one(sql, dialect="postgres")
    except Exception as e:
        return False, f"SQL语法错误: {e}"

    if parsed.key != "select":
        return False, "只允许 SELECT 查询操作"

    # 提取所有引用的表名
    used_tables = set()
    for table_node in parsed.find_all(sqlglot.exp.Table):
        name = table_node.name.lower() if table_node.name else ""
        if name:
            used_tables.add(name)

    forbidden = used_tables - allowed_table_names
    if forbidden:
        return False, f"引用了未授权的表: {', '.join(forbidden)}"

    return True, ""


async def _execute_readonly(sql: str, timeout: int = 10) -> tuple[list[str], list[list[Any]], int]:
    """在只读事务中执行 SQL，返回 (columns, rows, total_rows)"""
    async def _run() -> tuple[list, list]:
        async with async_engine.connect() as conn:
            await conn.execute(text(f"SET LOCAL statement_timeout = {timeout * 1000}"))
            query_result = await conn.execute(text(sql))
            cols = list(query_result.keys())
            fetched_rows = [list(row) for row in query_result.fetchmany(1000)]
            return cols, fetched_rows

    columns, rows = await asyncio.wait_for(_run(), timeout=timeout + 2)
    return columns, rows, len(rows)


async def _interpret_result(question: str, columns: list[str], rows: list[list[Any]]) -> str:
    preview_rows = rows[:5]
    preview = "\t".join(columns) + "\n"
    for row in preview_rows:
        preview += "\t".join(str(v) for v in row) + "\n"
    system_prompt = "你是一个数据分析助手。用一句简洁的中文描述以下查询结果的含义，不要超过50个字。"
    user_prompt = f"用户问题：{question}\n\n查询结果（前{len(preview_rows)}行）：\n{preview}"
    try:
        return await call_llm(user_prompt, system_prompt, {"llm": {"temperature": 0.3, "max_tokens": 100}})
    except Exception as e:
        log.warning(f"[text2sql] 结果解释失败: {repr(e)}")
        return f"共返回 {len(rows)} 条记录。"


# ── 公开服务方法 ──────────────────────────────────────────────────────────────

class Text2SQLService:

    async def query(self, db: AsyncSession, question: str, user_id: int, clarification_answer: str | None = None) -> QueryResponse:
        start_ms = int(time.time() * 1000)
        full_question = f"{question}（{clarification_answer}）" if clarification_answer else question

        # 1. 歧义检测（有 clarification_answer 时跳过）
        if not clarification_answer:
            clarification = await _detect_ambiguity(question)
            if clarification:
                log_obj = Text2SQLQueryLog(
                    question=question, status='clarification', create_user=user_id
                )
                db.add(log_obj)
                await db.commit()
                await db.refresh(log_obj)
                return QueryResponse(log_id=log_obj.id, clarification=clarification)

        # 2. Schema 检索
        tables = await _retrieve_schema(db, full_question)
        if not tables:
            return QueryResponse(log_id=None, summary="没有找到可查询的数据表，请先在管理页面配置白名单表。")

        allowed_table_names = {t.table_name.lower() for t in tables}
        schema_context = _build_schema_context(tables)

        # 3. Few-shot 检索
        examples = await _retrieve_examples(db, full_question)
        few_shot_context = _build_few_shot_context(examples)

        # 4. SQL 生成 + 校验 + 执行（带 self-correction）
        sql = await _generate_sql(full_question, schema_context, few_shot_context)
        retry_count = 0
        columns, rows, warning_msg = [], [], None

        for attempt in range(3):  # 最多重试 2 次
            ok, err = _validate_sql(sql, allowed_table_names)
            if not ok:
                if attempt < 2:
                    sql = await _fix_sql(full_question, sql, err, schema_context)
                    retry_count += 1
                    continue
                else:
                    elapsed = int(time.time() * 1000) - start_ms
                    log_obj = await self._save_log(
                        db, question=full_question, sql=sql, status='error',
                        error=err, retry_count=retry_count, elapsed_ms=elapsed, user_id=user_id
                    )
                    return QueryResponse(log_id=log_obj.id, summary=f"SQL 校验失败：{err}")

            try:
                columns, rows, _ = await _execute_readonly(sql)
                if len(rows) >= 1000:
                    warning_msg = "结果已截断，仅显示前 1000 行"
                break
            except asyncio.TimeoutError:
                elapsed = int(time.time() * 1000) - start_ms
                log_obj = await self._save_log(
                    db, question=full_question, sql=sql, status='timeout',
                    error="查询超时", retry_count=retry_count, elapsed_ms=elapsed, user_id=user_id
                )
                return QueryResponse(log_id=log_obj.id, summary="查询超时，请缩小查询范围后重试。")
            except Exception as e:
                err_str = repr(e)
                if attempt < 2:
                    sql = await _fix_sql(full_question, sql, err_str, schema_context)
                    retry_count += 1
                else:
                    elapsed = int(time.time() * 1000) - start_ms
                    log_obj = await self._save_log(
                        db, question=full_question, sql=sql, status='error',
                        error=err_str, retry_count=retry_count, elapsed_ms=elapsed, user_id=user_id
                    )
                    return QueryResponse(log_id=log_obj.id, summary=f"执行失败：{err_str}")

        # 5. 结果解释
        summary = await _interpret_result(full_question, columns, rows)
        elapsed = int(time.time() * 1000) - start_ms

        log_obj = await self._save_log(
            db, question=full_question, sql=sql, status='success',
            retry_count=retry_count, elapsed_ms=elapsed, row_count=len(rows), user_id=user_id
        )

        # rows 中可能含有非 JSON 可序列化值（Decimal、date 等），统一转 str
        serializable_rows = [[str(v) if not isinstance(v, (int, float, bool, type(None), str)) else v for v in row] for row in rows]

        return QueryResponse(
            log_id=log_obj.id,
            sql=sql,
            columns=columns,
            rows=serializable_rows,
            summary=summary,
            warning=warning_msg,
            execution_time_ms=elapsed,
        )

    async def _save_log(
        self, db: AsyncSession, *, question: str, sql: str | None = None,
        status: str, error: str | None = None, retry_count: int = 0,
        elapsed_ms: int = 0, row_count: int | None = None, user_id: int | None = None,
    ) -> Text2SQLQueryLog:
        log_obj = Text2SQLQueryLog(
            question=question,
            generated_sql=sql,
            status=status,
            error_message=error,
            row_count=row_count,
            execution_time_ms=elapsed_ms,
            retry_count=retry_count,
            create_user=user_id,
        )
        db.add(log_obj)
        await db.commit()
        await db.refresh(log_obj)
        return log_obj

    async def submit_feedback(self, db: AsyncSession, log_id: int, rating: int, correct_sql: str | None) -> None:
        log_obj = await crud_text2sql_query_log.get(db, log_id)
        if not log_obj:
            return
        log_obj.feedback = rating
        if correct_sql:
            log_obj.feedback_sql = correct_sql
        await db.commit()

    # ── 元数据管理 ────────────────────────────────────────────────────────────

    async def get_available_tables(self, db: AsyncSession) -> list[dict]:
        """从 information_schema 获取所有用户表，标记哪些已导入白名单"""
        result = await db.execute(
            text(
                "SELECT table_schema, table_name FROM information_schema.tables "
                "WHERE table_schema NOT IN ('pg_catalog', 'information_schema') "
                "AND table_type = 'BASE TABLE' "
                "ORDER BY table_schema, table_name"
            )
        )
        all_tables = result.fetchall()
        imported = {(s, n) for s, n in await crud_text2sql_table.get_all_table_names(db)}
        return [
            {
                "schema_name": row[0],
                "table_name": row[1],
                "is_imported": (row[0], row[1]) in imported,
            }
            for row in all_tables
        ]

    async def import_tables(self, db: AsyncSession, table_names: list[str], user_id: int) -> list[Text2SQLTable]:
        """从 information_schema 批量导入表结构到白名单"""
        imported = []
        for full_name in table_names:
            parts = full_name.split(".", 1)
            schema_name = parts[0] if len(parts) == 2 else "public"
            table_name = parts[1] if len(parts) == 2 else parts[0]

            existing = await crud_text2sql_table.get_by_table_name(db, schema_name, table_name)
            if existing:
                imported.append(existing)
                continue

            table_obj = Text2SQLTable(
                schema_name=schema_name, table_name=table_name, create_user=user_id
            )
            db.add(table_obj)
            await db.flush()  # 获得 id

            # 从 information_schema 拉取字段
            col_result = await db.execute(
                text(
                    "SELECT column_name, data_type, ordinal_position "
                    "FROM information_schema.columns "
                    "WHERE table_schema = :schema AND table_name = :table "
                    "ORDER BY ordinal_position"
                ),
                {"schema": schema_name, "table": table_name},
            )
            for col_row in col_result.fetchall():
                col_obj = Text2SQLColumn(
                    table_id=table_obj.id,
                    column_name=col_row[0],
                    data_type=col_row[1],
                    ordinal_position=col_row[2],
                )
                db.add(col_obj)

            await db.commit()
            await db.refresh(table_obj)
            imported.append(table_obj)
        return imported

    async def embed_table(self, db: AsyncSession, table_id: int) -> bool:
        """对表的 description 进行向量化并存储"""
        table_obj = await crud_text2sql_table.get(db, table_id)
        if not table_obj or not table_obj.description:
            return False
        results = await embed_texts([table_obj.description])
        if results:
            table_obj.embedding = results[0]["embs"]
            await db.commit()
            return True
        return False

    async def embed_example(self, db: AsyncSession, example_id: int) -> bool:
        """对 Few-shot 示例的 question 进行向量化"""
        example = await crud_text2sql_example.get(db, example_id)
        if not example:
            return False
        results = await embed_texts([example.question])
        if results:
            example.question_embedding = results[0]["embs"]
            await db.commit()
            return True
        return False

    async def create_example_from_feedback(self, db: AsyncSession, log_id: int, user_id: int) -> Text2SQLExample | None:
        """将用户反馈的正确 SQL 转为 Few-shot 示例"""
        log_obj = await crud_text2sql_query_log.get(db, log_id)
        if not log_obj or not log_obj.feedback_sql:
            return None
        example = Text2SQLExample(
            question=log_obj.question,
            sql=log_obj.feedback_sql,
            source='feedback',
            create_user=user_id,
        )
        db.add(example)
        await db.commit()
        await db.refresh(example)
        await self.embed_example(db, example.id)
        return example


text2sql_service = Text2SQLService()
