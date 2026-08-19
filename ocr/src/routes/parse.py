"""
POST /parse — OCR 解析
GET  /health — 健康检查
"""

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, UploadFile
from mineru.cli.common import aio_do_parse

from src.config import settings
from src.schemas import HealthResponse, ParseResponse

router = APIRouter()

# 合法的 task 值
VALID_TASKS = {"default", "double_page"}

# MinerU pipeline 后端要求 PDF 输入，图片需先转换
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp", ".gif", ".jp2"}


def _strip_html(html: str) -> str:
    """去掉 HTML 标签，保留纯文本。"""
    import re
    return re.sub(r'<[^>]+>', ' ', html).strip()


def _extract_v2_text(block: dict) -> str:
    """从 content_list_v2 的 block 中递归提取纯文本。

    处理 paragraph / title / table / page_number 等类型，
    table 的 html 内容会自动剥离标签。
    """
    if not isinstance(block, dict):
        return ""
    if block.get("type") == "text":
        return block.get("content", "")

    inner = block.get("content", {})
    if not isinstance(inner, dict):
        return ""

    parts: list[str] = []
    for key, val in inner.items():
        if isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    parts.append(_extract_v2_text(item))
                elif isinstance(item, str):
                    parts.append(item)
        elif isinstance(val, str):
            if key in ("html", "table_body"):
                parts.append(_strip_html(val))
    return " ".join(p for p in parts if p.strip())


def _ensure_pdf_bytes(filename: str, raw: bytes) -> bytes:
    """图片 → PDF bytes；PDF/Office 文件原样返回。"""
    suffix = Path(filename).suffix.lower()
    if suffix not in IMAGE_SUFFIXES:
        return raw

    from PIL import Image
    import io

    img = Image.open(io.BytesIO(raw))
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PDF")
    return buf.getvalue()


@router.post("/parse", response_model=ParseResponse)
async def parse(
    file: UploadFile = Form(...),
    task: str = Form(default="default"),
):
    """接收文档文件，返回全文 + 分页内容。"""

    # ---- 1. 参数校验 ----
    if task not in VALID_TASKS:
        raise HTTPException(
            status_code=400,
            detail=f"task 取值必须为 {sorted(VALID_TASKS)}，当前值: {task!r}",
        )

    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供文件名")

    file_bytes = await file.read()
    if len(file_bytes) > settings.max_file_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"文件大小超过限制 ({settings.max_file_mb} MB)",
        )

    # ---- 2. 准备 MinerU 参数 ----
    task_id = uuid.uuid4().hex[:12]
    file_stem = Path(file.filename).stem
    output_dir = Path(settings.output_dir) / task_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # 双页排版：如果 MinerU 内部不支持，可在此用 PyMuPDF 预切页后重新喂入
    # 当前先统一透传，后续根据实际效果调整。
    parse_method = settings.parse_method
    if task == "double_page":
        # TODO: 双页模式可能需要 PDF 页面竖切预处理，或调整 MinerU 的 layout 参数
        pass

    # ---- 3. 调用 MinerU 引擎 ----
    pdf_bytes = _ensure_pdf_bytes(file.filename, file_bytes)
    try:
        await aio_do_parse(
            output_dir=str(output_dir),
            pdf_file_names=[file_stem],
            pdf_bytes_list=[pdf_bytes],
            p_lang_list=[settings.default_lang],
            backend=settings.default_backend,
            parse_method=parse_method,
            formula_enable=True,
            table_enable=True,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"MinerU 解析失败: {exc}",
        )

    # ---- 4. 收集结果 —— MinerU 结果在 {output}/{stem}/{parse_method}/ 下 -——
    def _find(pattern: str) -> Path | None:
        hits = sorted(output_dir.rglob(pattern))
        return hits[0] if hits else None

    md_path = _find(f"{file_stem}.md")
    cl_path = _find(f"{file_stem}_content_list_v2.json") or _find(f"{file_stem}_content_list.json")

    if not md_path:
        raise HTTPException(
            status_code=500,
            detail=f"MinerU 解析完成但未生成预期输出文件，目录内容: {sorted(output_dir.rglob('*'))}",
        )

    # 全文
    content = md_path.read_text(encoding="utf-8")

    # 分页内容
    pages_content: list[str] = []
    if cl_path and cl_path.exists():
        try:
            with open(cl_path, encoding="utf-8") as f:
                data = json.load(f)
            if data:
                # content_list_v2: 按页嵌套 [[page0_blocks], [page1_blocks], ...]
                # content_list_v1: 平铺 [{page_idx, text/md}, ...]
                if isinstance(data[0], list):
                    for page_blocks in data:
                        texts = [_extract_v2_text(b) for b in page_blocks]
                        pages_content.append("\n".join(t for t in texts if t.strip()))
                else:
                    page_map: dict[int, list[str]] = {}
                    for block in data:
                        if not isinstance(block, dict):
                            continue
                        page_idx = block.get("page_idx", 0)
                        # 优先用 text 字段；表格用 table_caption + table_body
                        text = block.get("text", "")
                        if not text.strip() and block.get("type") == "table":
                            text = _extract_v2_text(block)
                        if text.strip():
                            page_map.setdefault(page_idx, []).append(text)
                    pages_content = [
                        "\n".join(page_map[i])
                        for i in sorted(page_map)
                    ]
        except (json.JSONDecodeError, KeyError):
            pages_content = []

    # ---- 5. 清理落盘 ----
    if settings.cleanup_after_parse:
        import shutil
        shutil.rmtree(output_dir, ignore_errors=True)

    return ParseResponse(content=content, pages_content=pages_content)


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        backend=settings.default_backend,
        max_file_mb=settings.max_file_mb,
    )
