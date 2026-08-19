"""
测试 aio_do_parse 核心函数是否能正常工作。

Usage:
    python tests/test_parse.py                      # 自动生成测试图片
    python tests/test_parse.py path/to/doc.pdf       # 指定 PDF/图片
"""

import asyncio
import json
import sys
from pathlib import Path

from mineru.cli.common import aio_do_parse

OUTPUT_DIR = Path("./test_output")


def create_test_image(path: str):
    """用 Pillow 生成含中英文的测试图片，无需外部文件。"""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (800, 200), "white")
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), "Hello World", fill="black")
    draw.text((20, 60), "这是一段测试文本 for OCR testing.", fill="black")
    draw.text((20, 100), "MinerU 文档解析测试 12345", fill="black")
    img.save(path)
    print(f"🖼️  已生成测试图片: {path}")


def _to_pdf_bytes(file_path: Path) -> bytes:
    """将图片转为 PDF bytes；PDF 文件直接返回。"""
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return file_path.read_bytes()

    from PIL import Image
    import io

    img = Image.open(file_path)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PDF")
    return buf.getvalue()


async def test_parse(file_path: str):
    file_path = Path(file_path)
    pdf_bytes = _to_pdf_bytes(file_path)
    file_stem = file_path.stem

    OUTPUT_DIR.mkdir(exist_ok=True)

    print(f"📄 文件: {file_path.name}  ({len(pdf_bytes)} bytes)")
    print(f"📁 输出: {OUTPUT_DIR.resolve()}")
    print(f"⏳ 正在解析...\n")

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

    print("✅ 解析完成!\n")

    # 检查输出文件 —— MinerU 会将结果放在 {output}/{stem}/{parse_method}/ 目录下
    def _find(pattern: str) -> Path | None:
        hits = sorted(OUTPUT_DIR.rglob(pattern))
        return hits[0] if hits else None

    md_file = _find(f"{file_stem}.md")
    # 优先新版 content_list
    cl_file = _find(f"{file_stem}_content_list_v2.json") or _find(f"{file_stem}_content_list.json")

    if md_file.exists():
        content = md_file.read_text("utf-8")
        print(f"📝 Markdown ({len(content)} 字符):")
        print("-" * 40)
        print(content[:1500])
        if len(content) > 1500:
            print("    ...(截断)")
    else:
        print("⚠️  未找到 .md 输出文件")
        print(f"   目录内容: {list(OUTPUT_DIR.rglob('*'))}")

    if cl_file and cl_file.exists():
        with open(cl_file, encoding="utf-8") as f:
            data = json.load(f)
        print(f"\n📊 content_list: {len(data)} 顶层项")
        if data:
            if isinstance(data[0], list):
                for i, page in enumerate(data):
                    total = sum(len(b.get("content", b.get("text",""))) for b in page if isinstance(b, dict))
                    print(f"   第 {i} 页 → {len(page)} 个块")
            else:
                pages: dict[int, int] = {}
                for b in data:
                    p = b.get("page_idx", 0)
                    pages[p] = pages.get(p, 0) + 1
                for p, n in sorted(pages.items()):
                    print(f"   第 {p} 页 → {n} 个块")
        else:
            print("   (空)")
    else:
        print("⚠️  未找到 content_list")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        test_img = Path("./test_input.png")
        try:
            create_test_image(str(test_img))
        except ImportError:
            print("❌ 请安装 Pillow:  uv add Pillow")
            print("   或手动指定测试文件:  python tests/test_parse.py doc.pdf")
            sys.exit(1)
        target = str(test_img)

    asyncio.run(test_parse(target))
