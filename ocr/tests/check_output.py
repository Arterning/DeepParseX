"""检查 MinerU 输出的实际结构。"""
import json, sys
from pathlib import Path

base = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("test_output")

# ---- .md 文件 ----
md_files = sorted(base.rglob("*.md"))
if md_files:
    md = md_files[0].read_text()
    print(f"=== {md_files[0].relative_to(base)}  ({len(md)} 字符) ===")
    print(md[:800])
    print()

# ---- model.json ----
model_files = sorted(base.rglob("*_model.json"))
if model_files:
    m = json.loads(model_files[0].read_text())
    print(f"=== {model_files[0].relative_to(base)}  ({len(m)} 顶层项) ===")
    if m:
        first = m[0]
        if isinstance(first, dict):
            print(f"keys: {list(first.keys())}")
            print(json.dumps(first, indent=2, ensure_ascii=False)[:1200])
        else:
            print(f"第一条类型: {type(first).__name__}")
    print()

# ---- content_list ----
for name in ["content_list.json", "content_list_v2.json"]:
    found = sorted(base.rglob(f"*_{name}"))
    if not found:
        print(f"⚠️  未找到 *_{name}\n")
        continue
    path = found[0]
    data = json.loads(path.read_text())
    print(f"=== {path.relative_to(base)}  (顶层 {len(data)} 项) ===")
    if data:
        first = data[0]
        if isinstance(first, dict):
            print(f"第一条 keys: {list(first.keys())}")
            print(json.dumps(first, indent=2, ensure_ascii=False))
        elif isinstance(first, list):
            print(f"第一条是 list，长度={len(first)}")
            if first:
                print(json.dumps(first[0], indent=2, ensure_ascii=False))
        else:
            print(f"第一条类型: {type(first).__name__} = {first!r}")
    else:
        print("空数组 []")
    print()
