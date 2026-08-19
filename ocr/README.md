# lda-ocr

基于 [MinerU](https://github.com/opendatalab/MinerU) 的文档 OCR API 服务。

## 快速开始

```bash
# 安装依赖
uv sync

# 首次运行需下载模型（国内用 modelscope 源）
export MINERU_MODEL_SOURCE=modelscope

# 启动服务
python main.py
# → http://localhost:8000/docs
```

```bash
# 调用
curl -X POST http://localhost:8000/parse \
  -F "file=@document.pdf" \
  -F "task=default"
```

## 接口

### POST /parse

`multipart/form-data`

| 字段 | 类型 | 说明 |
|------|------|------|
| `file` | file | PDF / 图片 / DOCX / PPTX / XLSX |
| `task` | str | `"default"` — 普通文档；`"double_page"` — 双页排版 |

响应：

```json
{
  "content": "全文 Markdown（表格→HTML，公式→LaTeX）",
  "pages_content": ["第1页文本", "第2页文本", "..."]
}
```

### GET /health

```json
{ "status": "ok", "backend": "pipeline", "max_file_mb": 100 }
```

## MinerU 输出文件说明

MinerU 解析后在输出目录生成以下文件，以 `test_input.pdf` 为例：

```
output/test_input/auto/
├── test_input.md                    ← 最终产物
├── test_input_content_list.json     ← 最终产物 v1（平铺）
├── test_input_content_list_v2.json  ← 最终产物 v2（按页分组）
├── test_input_middle.json           ← 中间产物
├── test_input_model.json            ← 中间产物
├── test_input_layout.pdf            ← 调试可视化
├── test_input_span.pdf              ← 调试可视化
├── test_input_origin.pdf            ← 原始文档副本
└── images/                          ← 提取的图片
```

### 最终产物

| 文件 | 说明 |
|------|------|
| `.md` | 全文 Markdown，表格→HTML 表格，公式→LaTeX，按阅读顺序排列 |
| `_content_list.json` | v1：平铺内容块数组 `[{type, text, page_idx, bbox, ...}]` |
| `_content_list_v2.json` | v2：同上但按页分组 `[[page0块...], [page1块...]]` |

### 中间产物（调试用）

| 文件 | 说明 |
|------|------|
| `_middle.json` | Pipeline 原始输出，所有检测元素（布局框、文字行、表格、公式）及坐标 |
| `_model.json` | 每页元信息：`page_info`（页码/宽高）+ `layout_dets`（布局检测结果） |

### 可视化 PDF（调试用）

| 文件 | 说明 |
|------|------|
| `_layout.pdf` | 在原文档上标注布局检测框（段落/标题/表格/图片区域） |
| `_span.pdf` | 在原文档上标注文字行级别的检测框 |
| `_origin.pdf` | 输入文档的原样副本 |

### `images/`

文档中提取出的嵌入图片。

## 配置

通过环境变量覆盖默认值（前缀 `OCR_`）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OCR_DEFAULT_LANG` | `ch` | OCR 语言 |
| `OCR_DEFAULT_BACKEND` | `pipeline` | `pipeline` / `vlm-engine` / `hybrid-engine` |
| `OCR_PORT` | `8000` | 服务端口 |
| `OCR_MAX_FILE_MB` | `100` | 上传文件大小上限 |
| `OCR_CLEANUP_AFTER_PARSE` | `true` | 解析后是否清理落盘临时文件 |

## 模型下载

首次运行 MinerU 会从 HuggingFace 下载模型（数 GB）。国内网络建议：

```bash
export MINERU_MODEL_SOURCE=modelscope
# 或
export HF_ENDPOINT=https://hf-mirror.com
```

## 项目结构

```
lda-ocr/
├── pyproject.toml
├── main.py                  # 入口：uvicorn 启动
├── README.md
├── src/
│   ├── app.py               # FastAPI app 工厂
│   ├── config.py            # 配置（Settings dataclass）
│   ├── schemas.py           # Pydantic 请求/响应模型
│   └── routes/
│       └── parse.py         # POST /parse + GET /health
└── tests/
    ├── test_parse.py        # aio_do_parse 核心函数测试
    └── check_output.py      # MinerU 输出结构检查
```
