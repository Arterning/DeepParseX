# MinerU content_list JSON 结构说明

`content_list.json`（v1）和 `content_list_v2.json`（v2）是 MinerU pipeline 输出的结构化内容文件，记录每页的文本块、标题、表格等信息。本文档基于实际输出归纳。

---

## content_list.json（v1）

### 顶层结构

平铺数组，每个元素是一个内容块，按阅读顺序排列，跨页不分组。

```json
[
  { "type": "text", "text": "...", "bbox": [...], "page_idx": 0 },
  { "type": "text", "text": "...", "bbox": [...], "page_idx": 0 },
  { "type": "table", "text": "", "table_body": "<table>...", "page_idx": 1 }
]
```

### 公共字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | string | 块类型：`text` / `table` / `page_number` |
| `bbox` | `[x1, y1, x2, y2]` | 边界框坐标 |
| `page_idx` | int | 页码（0 起始） |

### 各类型特有字段

#### `text`

```json
{
  "type": "text",
  "text": "正文内容",
  "text_level": 2,
  "bbox": [137, 274, 314, 291],
  "page_idx": 0
}
```

| 字段 | 说明 |
|------|------|
| `text` | 纯文本内容 |
| `text_level` | 仅标题出现，表示层级（1/2/3...） |

#### `table`

```json
{
  "type": "table",
  "text": "",
  "img_path": "images/xxx.jpg",
  "table_caption": ["1. 表格标题"],
  "table_footnote": [],
  "table_body": "<table><tr>...</tr></table>",
  "bbox": [98, 413, 894, 836],
  "page_idx": 1
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `text` | string | **始终为空** `""`，不要依赖 |
| `img_path` | string | 表格截图路径 |
| `table_caption` | `string[]` | 表格标题，**纯字符串数组**（非 dict） |
| `table_footnote` | `string[]` | 表格脚注 |
| `table_body` | string | 表格内容的 HTML 字符串 |

> **提取文本**：拼接 `table_caption` + 对 `table_body` 剥离 HTML 标签。

#### `page_number`

```json
{
  "type": "page_number",
  "text": "3",
  "bbox": [487, 897, 506, 915],
  "page_idx": 2
}
```

`text` 字段直接就是页码数字。

---

## content_list_v2.json（v2）

### 顶层结构

**按页嵌套**的二维数组。外层每个元素是一页，内层是该页的内容块列表。

```json
[
  [ {page 0 的块...} ],
  [ {page 1 的块...} ],
  [ {page 2 的块...} ]
]
```

### 公共字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | string | 块类型：`paragraph` / `title` / `table` / `page_number` |
| `bbox` | `[x1, y1, x2, y2]` | 边界框坐标 |
| `content` | object | 所有文本内容均嵌套在此对象中 |

### 提取规则

**文本永远不直接出现在块顶层**。必须递归进入 `content` → 各子键 → 子元素的 `content` 字段。

#### `text`（叶子节点）

所有文本最终都落脚到这种叶子节点：

```json
{ "type": "text", "content": "实际文字内容" }
```

提取：取 `content` 字段。

#### `paragraph`

```json
{
  "type": "paragraph",
  "content": {
    "paragraph_content": [
      { "type": "text", "content": "段落文字1" },
      { "type": "text", "content": "段落文字2" }
    ]
  },
  "bbox": [136, 296, 862, 355]
}
```

提取：遍历 `content.paragraph_content[]`，对每个元素递归取 `content`。

#### `title`

```json
{
  "type": "title",
  "content": {
    "title_content": [
      { "type": "text", "content": "标题文字" }
    ],
    "level": 2
  },
  "bbox": [137, 274, 314, 291]
}
```

提取：遍历 `content.title_content[]`，递归取 `content`。`content.level` 是标题层级（忽略）。

#### `table`

```json
{
  "type": "table",
  "content": {
    "image_source": { "path": "images/xxx.jpg" },
    "table_caption": [
      { "type": "text", "content": "1. 表格标题" }
    ],
    "table_footnote": [],
    "html": "<table><tr><td>...</td></tr></table>",
    "table_type": "complex_table",
    "table_nest_level": 1
  },
  "bbox": [98, 413, 894, 836]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `image_source` | `{"path": "..."}` | 表格截图，**dict 类型**（非 string） |
| `table_caption` | dict[] | 表格标题，元素为 `{type:"text", content:"..."}` |
| `table_footnote` | dict[] | 脚注，同 caption 结构 |
| `html` | string | 表格内容的 HTML 字符串 |
| `table_type` | string | `simple_table` / `complex_table` |
| `table_nest_level` | int | 嵌套层级 |

> **提取文本**：递归提取 `table_caption` + `table_footnote` 中的文字，对 `html` 字段剥离 HTML 标签。

#### `page_number`

```json
{
  "type": "page_number",
  "content": {
    "page_number_content": [
      { "type": "text", "content": "3" }
    ]
  },
  "bbox": [487, 897, 506, 915]
}
```

提取：遍历 `content.page_number_content[]`，递归取 `content`。

---

## v1 vs v2 对比

| 维度 | v1 | v2 |
|------|----|----|
| 结构 | 平铺数组 | 按页嵌套 `[[], [], ...]` |
| 分页 | `page_idx` 字段 | 外层数组索引 |
| 文本位置 | `block.text` | 递归：`block.content.{*}_content[].content` |
| 表格标题 | 字符串数组 `["text"]` | dict 数组 `[{type:"text", content:"text"}]` |
| 表格正文 | `table_body` (HTML) | `html` (HTML) |
| 表格截图 | `img_path` (string) | `image_source.path` (嵌套 dict) |

---

## 已知坑点

### 1. 跨页表格的延续页无文本

MinerU 将完整 HTML 只放在表格起始页，后续溢出页的 table 块 `html` 为空、`table_caption` 为空，仅保留 `image_source`。代码需容忍某页提取出 0 字符文本。

### 2. `simple_table` 无 HTML

`table_type: "simple_table"` 的表格通常无 `html` 字段或为空，文字存在于截图中。这种情况只能依赖截图，无法提取文本。

### 3. v1 表格 `text` 始终为空

不要用 v1 的 `text` 字段判断表格是否有内容 —— 它永远是 `""`。必须从 `table_caption` + `table_body` 提取。

### 4. v2 `image_source` 是 dict

```json
// v2
"image_source": { "path": "images/xxx.jpg" }

// v1
"img_path": "images/xxx.jpg"
```

v2 中 `image_source` 是对象而非字符串，遍历 `content` 的键值对时需跳过 dict 类型的值。
