"""
数据分析工具执行函数

- data_schema: 查看表格文档的结构（列名、类型、样例、行数）
- data_analysis: 对表格文档执行 DuckDB SQL 查询

只会对 type 为 spreadsheet / csv 的文档生效。
参考 WeKnora 的 data_schema.go + data_analysis.go。
"""
import asyncio
import re
from typing import Any

import duckdb

from backend.common.log import log
from backend.database.db_pg import async_db_session


# 最大返回行数
MAX_RESULT_ROWS = 200

# 允许的 SQL 语句类型（只读）
ALLOWED_SQL_PREFIXES = {"SELECT", "SHOW", "DESCRIBE", "EXPLAIN", "PRAGMA", "WITH"}


def _infer_type(value: Any) -> str:
    """从 Python 值推断 DuckDB 类型"""
    if value is None:
        return "VARCHAR"
    if isinstance(value, bool):
        return "BOOLEAN"
    if isinstance(value, int):
        return "BIGINT"
    if isinstance(value, float):
        return "DOUBLE"
    return "VARCHAR"


def _infer_display_type(value: Any) -> str:
    """从 Python 值推断前端展示类型名"""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    return "string"


async def execute_data_schema(doc_id: int) -> dict:
    """
    查看表格文档结构。

    流程：
    1. 查 sys_doc 验证存在且 type=spreadsheet/csv
    2. 查 sys_doc_data 前 3 行推断列信息和类型
    3. 查总行数
    """
    from sqlalchemy import select, func
    from backend.app.admin.model import SysDoc, SysDocData

    async with async_db_session() as db:
        # 1. 验证文档
        doc_result = await db.execute(
            select(SysDoc.id, SysDoc.title, SysDoc.type).where(SysDoc.id == doc_id)
        )
        doc_row = doc_result.first()
        if not doc_row:
            return {"error": f"文档 {doc_id} 不存在"}

        doc_id_val, title, doc_type = doc_row

        if doc_type not in ("spreadsheet", "csv"):
            return {
                "error": f"文档类型为 {doc_type}，不支持表格分析。"
                f"仅支持 spreadsheet 或 csv 类型。",
            }

        # 2. 取样行 + 总行数
        sample_result = await db.execute(
            select(SysDocData.row)
            .where(SysDocData.doc_id == doc_id)
            .limit(3)
        )
        sample_rows = [r[0] for r in sample_result.all()]

        count_result = await db.execute(
            select(func.count()).select_from(SysDocData).where(SysDocData.doc_id == doc_id)
        )
        total_rows = count_result.scalar() or 0

    if total_rows == 0:
        return {
            "title": title,
            "type": doc_type,
            "total_rows": 0,
            "columns": [],
            "hint": "该文档无数据行",
        }

    # 3. 推断列信息
    columns = []
    if sample_rows:
        # 收集所有列名
        all_keys = list(dict.fromkeys(  # 去重保序
            k for row in sample_rows if isinstance(row, dict) for k in row.keys()
        ))

        for col_name in all_keys:
            # 收集该列的样例值
            samples = [
                row.get(col_name) for row in sample_rows
                if isinstance(row, dict) and col_name in row
            ]
            # 以最常见的非空类型为准
            types = [_infer_display_type(v) for v in samples if v is not None]
            col_type = max(set(types), key=types.count) if types else "null"
            sample_val = next((v for v in samples if v is not None), None)

            columns.append({
                "name": col_name,
                "type": col_type,
                "sample": sample_val,
            })

    return {
        "title": title,
        "type": doc_type,
        "total_rows": total_rows,
        "columns": columns,
        "hint": f"共 {len(columns)} 列，{total_rows} 行。使用 data_analysis 执行 SQL 查询，表名为 t。",
    }


async def execute_data_analysis(doc_id: int, sql: str) -> dict:
    """
    对表格文档执行 DuckDB SQL 查询。

    安全措施（对标 WeKnora）：
    - 只允许 SELECT/SHOW/DESCRIBE/EXPLAIN/PRAGMA/WITH
    - 表名固定为 t（白名单）
    - 结果行数限制 MAX_RESULT_ROWS
    """
    from sqlalchemy import select, func
    from backend.app.admin.model import SysDoc, SysDocData

    # ── SQL 安全校验 ──
    sql_stripped = sql.strip()
    sql_upper = sql_stripped.upper()

    # 检查语句类型
    allowed = False
    for prefix in ALLOWED_SQL_PREFIXES:
        if sql_upper.startswith(prefix):
            allowed = True
            break

    if not allowed:
        return {
            "error": (
                f"不支持的 SQL 语句类型。仅支持: {', '.join(sorted(ALLOWED_SQL_PREFIXES))}。"
                f"收到的语句以 '{sql_stripped.split()[0] if sql_stripped.split() else sql_stripped[:20]}' 开头。"
            ),
        }

    # 检查多语句攻击
    statements = [s.strip() for s in sql_stripped.split(";") if s.strip()]
    if len(statements) > 1:
        return {"error": "不允许执行多条 SQL 语句"}

    # ── 加载数据 ──
    async with async_db_session() as db:
        # 验证文档
        doc_result = await db.execute(
            select(SysDoc.id, SysDoc.title, SysDoc.type).where(SysDoc.id == doc_id)
        )
        doc_row = doc_result.first()
        if not doc_row:
            return {"error": f"文档 {doc_id} 不存在"}

        doc_id_val, title, doc_type = doc_row
        if doc_type not in ("spreadsheet", "csv"):
            return {"error": f"文档类型 {doc_type} 不支持表格分析"}

        # 加载全部数据行
        data_result = await db.execute(
            select(SysDocData.row).where(SysDocData.doc_id == doc_id)
        )
        rows = [r[0] for r in data_result.all()]

    if not rows:
        return {"error": "文档无数据行"}

    # ── DuckDB 建表 + 导入 ──

    # 收集所有列名（保序）
    all_keys = list(dict.fromkeys(
        k for row in rows if isinstance(row, dict) for k in row.keys()
    ))
    if not all_keys:
        return {"error": "数据行为空或无有效列"}

    # 为每列推断 DuckDB 类型（以非空值中最常见的为准）
    col_types: dict[str, str] = {}
    for col_name in all_keys:
        values = [
            row.get(col_name) for row in rows
            if isinstance(row, dict) and col_name in row and row.get(col_name) is not None
        ]
        if values:
            types = [_infer_type(v) for v in values]
            col_types[col_name] = max(set(types), key=types.count)
        else:
            col_types[col_name] = "VARCHAR"

    # 清理列名：替换特殊字符为下划线，确保是合法 SQL 标识符
    def _clean_col(name: str) -> str:
        return re.sub(r"[^a-zA-Z0-9_\u4e00-\u9fff]", "_", name)

    clean_keys = [_clean_col(k) for k in all_keys]
    key_map = dict(zip(all_keys, clean_keys))

    try:
        loop = asyncio.get_running_loop()

        # DuckDB 操作在线程池中执行
        def _duckdb_query():
            conn = duckdb.connect(":memory:")
            try:
                # 建表
                col_defs = ", ".join(
                    f'"{clean_keys[i]}" {col_types[all_keys[i]]}'
                    for i in range(len(all_keys))
                )
                conn.execute(f'CREATE TABLE t ({col_defs})')

                # 插入数据
                placeholders = ", ".join("?" for _ in all_keys)
                insert_sql = f'INSERT INTO t VALUES ({placeholders})'
                batch = []
                for row in rows:
                    if isinstance(row, dict):
                        batch.append([row.get(k) for k in all_keys])
                conn.executemany(insert_sql, batch)

                # 执行用户 SQL（LIMIT 保护）
                safe_sql = sql_stripped.rstrip(";").strip()
                # 如果用户没写 LIMIT，自动加
                if "LIMIT" not in safe_sql.upper():
                    safe_sql = f"SELECT * FROM ({safe_sql}) AS _sub LIMIT {MAX_RESULT_ROWS}"

                result = conn.execute(safe_sql)
                col_names = [desc[0] for desc in result.description]
                rows_data = result.fetchall()

                return col_names, rows_data
            finally:
                conn.close()

        col_names, result_rows = await loop.run_in_executor(None, _duckdb_query)

    except Exception as e:
        log.error(f"[data_analysis] DuckDB 执行失败: {repr(e)}")
        return {"error": f"SQL 执行失败: {str(e)}"}

    # ── 格式化输出 ──
    truncated = len(result_rows) > MAX_RESULT_ROWS
    result_rows = result_rows[:MAX_RESULT_ROWS]

    # 每行转为 dict
    items = [
        {col_names[i]: val for i, val in enumerate(row)}
        for row in result_rows
    ]

    return {
        "sql": sql,
        "total_rows": len(result_rows),
        "truncated": truncated,
        "columns": col_names,
        "data": items,
        "hint": (
            f"返回 {len(result_rows)} 行。"
            + ("结果已截断，建议添加更精确的 WHERE/GROUP BY。" if truncated else "")
        ),
    }
