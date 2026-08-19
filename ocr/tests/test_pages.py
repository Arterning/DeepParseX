"""
测试分页内容提取 —— 打印 pages_content 数组。

Usage:
    python tests/test_pages.py path/to/document.pdf
"""

import asyncio
import json
import sys
from pathlib import Path

from mineru.cli.common import aio_do_parse

OUTPUT_DIR = Path("./test_output")
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp", ".gif", ".jp2"}


def _to_pdf_bytes(file_path: Path) -> bytes:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return file_path.read_bytes()
    from PIL import Image
    import io
    img = Image.open(file_path)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PDF")
    return buf.getvalue()


def _strip_html(html: str) -> str:
    import re
    return re.sub(r'<[^>]+>', ' ', html).strip()


def _extract_v2_text(block: dict) -> str:
    """从 content_list_v2 的 block 中递归提取纯文本。"""
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


def _extract_pages_content(output_dir: Path, file_stem: str) -> list[str]:
    """从 MinerU 输出中提取分页内容。"""
    cl_path = None
    for name in [f"{file_stem}_content_list_v2.json", f"{file_stem}_content_list.json"]:
        hits = sorted(output_dir.rglob(name))
        if hits:
            cl_path = hits[0]
            break

    if not cl_path:
        return []

    data = json.loads(cl_path.read_text())
    if not data:
        return []

    pages: list[str] = []
    if isinstance(data[0], list):
        for page_blocks in data:
            texts = [_extract_v2_text(b) for b in page_blocks]
            pages.append("\n".join(t for t in texts if t.strip()))
    else:
        page_map: dict[int, list[str]] = {}
        for block in data:
            if not isinstance(block, dict):
                continue
            p = block.get("page_idx", 0)
            t = block.get("text", "")
            if not t.strip() and block.get("type") == "table":
                t = _extract_v2_text(block)
            if t.strip():
                page_map.setdefault(p, []).append(t)
        pages = ["\n".join(page_map[i]) for i in sorted(page_map)]

    return pages


async def main(file_path: str):
    fp = Path(file_path)
    if not fp.exists():
        print(f"❌ 文件不存在: {file_path}")
        sys.exit(1)

    pdf_bytes = _to_pdf_bytes(fp)
    file_stem = fp.stem
    OUTPUT_DIR.mkdir(exist_ok=True)

    print(f"📄 {fp.name}  ({len(pdf_bytes)} bytes)")
    print(f"⏳ 解析中...\n")

    await aio_do_parse(
        output_dir=str(OUTPUT_DIR),
        pdf_file_names=[file_stem],
        pdf_bytes_list=[pdf_bytes],
        p_lang_list=["ch"],
        backend="pipeline",
        parse_method="auto",
        formula_enable=True,
        table_enable=True,
    )

    pages = _extract_pages_content(OUTPUT_DIR, file_stem)

    print(f"✅ 共 {len(pages)} 页\n")
    for i, text in enumerate(pages):
        print(f"{'='*60}")
        print(f"  📝 第 {i + 1} 页  ({len(text)} 字符)")
        print(f"{'='*60}")
        print(text[:600])
        if len(text) > 600:
            print(f"  ...(截断，全文 {len(text)} 字符)")
        print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tests/test_pages.py path/to/document.pdf")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
