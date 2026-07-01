"""
知识检索工具执行函数

对应 WeKnora 的 knowledge_search.go / grep_chunks.go / list_knowledge_chunks.go / get_document_info.go

每个函数接收 **kwargs 参数（从 LLM tool_call arguments JSON 解析），返回 dict。
结果会被 ToolRegistry 序列化为 JSON 字符串，超过 MAX_OUTPUT_CHARS 会被截断。
"""
from backend.common.log import log
from backend.app.admin.service.embedding_service import embed_text_chunks
from backend.app.admin.service.doc_service import sys_doc_service as doc_svc

# 工具输出最大字符数（对应 WeKnora 的 TruncateToolOutput）
MAX_OUTPUT_CHARS = 4000


async def execute_semantic_search(queries: list[str], top_k: int = 5) -> dict:
    """
    语义/向量检索：将每个查询向量化 → 并行向量检索 → 合并去重 → 排序

    参考 WeKnora knowledge_search.go 的 HybridSearch pipeline。
    """
    if not queries:
        return {"error": "queries 不能为空"}

    all_results = []
    seen_chunks: set[str] = set()

    for q in queries[:5]:  # 最多 5 个查询
        try:
            emb_result = await embed_text_chunks(q)
            query_vector = emb_result[0]["embs"]

            results = await doc_svc.search_similar_docs(
                query_vector=query_vector,
                limit=top_k,
                distance_threshold=1.2,
            )

            for r in results:
                chunk_key = f"{r.doc_id}:{r.chunk_text[:80] if r.chunk_text else ''}"
                if chunk_key not in seen_chunks:
                    seen_chunks.add(chunk_key)
                    chunk_text = (r.chunk_text or "")[:800]  # 单条限制 800 字符
                    all_results.append({
                        "doc_id": r.doc_id,
                        "doc_name": r.doc_name,
                        "chunk_text": chunk_text,
                        "score": getattr(r, "distance", None),
                        "query": q,
                    })
        except Exception as e:
            log.error(f"[semantic_search] 查询 '{q[:80]}' 失败: {repr(e)}")
            continue

    # 按 score 排序（distance 越小越相关）
    all_results.sort(key=lambda x: x.get("score") or 999)

    # 控制总输出量
    total_chars = sum(len(r["chunk_text"]) for r in all_results)
    truncated = False
    while total_chars > MAX_OUTPUT_CHARS and len(all_results) > 1:
        all_results.pop()
        total_chars = sum(len(r["chunk_text"]) for r in all_results)
        truncated = True

    return {
        "total": len(all_results),
        "truncated": truncated,
        "results": all_results,
    }


async def execute_keyword_search(query: str, top_k: int = 10) -> dict:
    """
    关键词全文检索：直接在数据库 pgvector 全文索引中搜索

    参考 WeKnora grep_chunks.go。
    """
    if not query or not query.strip():
        return {"error": "query 不能为空"}

    try:
        results = await doc_svc.search_fulltext_chunks(
            keyword=query.strip(),
            limit=min(top_k, 20),
        )

        items = []
        for r in results:
            chunk_text = (r.chunk_text or "")[:600]
            items.append({
                "doc_id": r.doc_id,
                "doc_name": r.doc_name,
                "chunk_text": chunk_text,
                "score": getattr(r, "rank", None),
            })

        # 输出截断
        total_chars = sum(len(it["chunk_text"]) for it in items)
        truncated = False
        while total_chars > MAX_OUTPUT_CHARS and len(items) > 1:
            items.pop()
            total_chars = sum(len(it["chunk_text"]) for it in items)
            truncated = True

        return {
            "total": len(items),
            "truncated": truncated,
            "results": items,
        }
    except Exception as e:
        log.error(f"[keyword_search] 搜索 '{query[:80]}' 失败: {repr(e)}")
        return {"error": repr(e)}


async def execute_get_chunks(doc_id: int, limit: int = 20) -> dict:
    """
    获取指定文档的所有分块内容

    参考 WeKnora list_knowledge_chunks.go。
    """
    from backend.database.db_pg import async_db_session
    from backend.app.admin.crud.crud_doc_chunk import sys_doc_chunk_dao

    try:
        async with async_db_session() as db:
            chunks = await sys_doc_chunk_dao.get_by_doc_id(db, doc_id)
            chunks = chunks[:min(limit, 50)]

        items = []
        for i, chunk in enumerate(chunks):
            text = (chunk.chunk_text or "")[:600]
            items.append({
                "index": i + 1,
                "chunk_text": text,
            })

        return {
            "doc_id": doc_id,
            "total_chunks": len(items),
            "chunks": items,
        }
    except Exception as e:
        log.error(f"[get_chunks] 获取文档 {doc_id} 分块失败: {repr(e)}")
        return {"error": repr(e)}


async def execute_get_doc_info(doc_id: int) -> dict:
    """
    获取文档元数据

    参考 WeKnora get_document_info.go。
    """
    from backend.database.db_pg import async_db_session
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from backend.app.admin.model import SysDoc

    try:
        async with async_db_session() as db:
            result = await db.execute(
                select(SysDoc)
                .options(selectinload(SysDoc.tags))
                .where(SysDoc.id == doc_id)
            )
            doc = result.scalar_one_or_none()

        if not doc:
            return {"error": f"文档 {doc_id} 不存在"}

        content_preview = ""
        if doc.content:
            content_preview = doc.content[:300] + ("..." if len(doc.content) > 300 else "")

        return {
            "doc_id": doc.id,
            "title": doc.title,
            "type": doc.type,
            "doc_dir_id": doc.doc_dir_id,
            "tags": [t.name for t in (doc.tags or [])],
            "content_preview": content_preview,
            "created_time": str(doc.created_time) if doc.created_time else None,
            "status": doc.status,
        }
    except Exception as e:
        log.error(f"[get_doc_info] 获取文档 {doc_id} 信息失败: {repr(e)}")
        return {"error": repr(e)}
