"""
工具定义（OpenAI function-calling JSON Schema）

对照 WeKnora 的 tools/definitions.go 设计：
- 每个工具的定义与执行函数分离
- 工具名用常量引用，避免字符串拼写错误
"""

# ── 工具名称常量（对应 WeKnora 的 ToolThinking / ToolKnowledgeSearch 等） ──

# 思考与规划
TOOL_THINKING = "thinking"
TOOL_TODO_WRITE = "todo_write"

# 知识检索
TOOL_SEMANTIC_SEARCH = "semantic_search"
TOOL_KEYWORD_SEARCH = "keyword_search"
TOOL_GET_CHUNKS = "get_chunks"
TOOL_GET_DOC_INFO = "get_doc_info"

# 网络工具
TOOL_WEB_SEARCH = "web_search"
TOOL_WEB_FETCH = "web_fetch"

# 数据分析
TOOL_DATA_SCHEMA = "data_schema"
TOOL_DATA_ANALYSIS = "data_analysis"

# Skills 系统
TOOL_READ_SKILL = "read_skill"
TOOL_EXECUTE_SKILL_SCRIPT = "execute_skill_script"

# 文件操作（已有）
TOOL_SEARCH_DOCS = "search_docs"
TOOL_CREATE_DOC_DIR = "create_doc_dir"
TOOL_MOVE_DOCS_TO_DIR = "move_docs_to_dir"
TOOL_CREATE_TEXT_DOC = "create_text_doc"
TOOL_CREATE_SPREADSHEET = "create_spreadsheet"
TOOL_LIST_DIRS = "list_dirs"
TOOL_GET_DOC_CONTENT = "get_doc_content"
TOOL_FIND_UNCLASSIFIED_DOCS = "find_unclassified_docs"
TOOL_TAG_DOC = "tag_doc"
TOOL_CREATE_PPT = "create_ppt"


# ── 思考与规划工具 ──

THINKING_SCHEMA = {
    "type": "object",
    "properties": {
        "thought": {
            "type": "string",
            "description": (
                "你当前的思考步骤。用自然、用户友好的语言书写。"
                "不要提及工具名称（如 semantic_search、keyword_search 等），"
                "而是用自然语言描述你的分析过程。"
                "专注于你要发现什么、为什么需要它，而不是怎么获取。"
            ),
        },
        "next_thought_needed": {
            "type": "boolean",
            "description": "是否需要继续下一步思考",
        },
        "thought_number": {
            "type": "integer",
            "description": "当前思考序号（1, 2, 3...）",
            "minimum": 1,
        },
        "total_thoughts": {
            "type": "integer",
            "description": "预估的总思考步数（可动态调整）",
            "minimum": 1,
        },
        "is_revision": {
            "type": "boolean",
            "description": "此步是否修正了之前的思考",
        },
        "revises_thought": {
            "type": "integer",
            "description": "被修正的思考步数编号",
            "minimum": 1,
        },
        "branch_from_thought": {
            "type": "integer",
            "description": "分支的起始思考步数编号",
            "minimum": 1,
        },
        "branch_id": {
            "type": "string",
            "description": "分支标识符",
        },
        "needs_more_thoughts": {
            "type": "boolean",
            "description": "如果在接近完成时意识到还需要更多思考",
        },
    },
    "required": ["thought", "next_thought_needed", "thought_number", "total_thoughts"],
}

TODO_WRITE_SCHEMA = {
    "type": "object",
    "properties": {
        "task": {
            "type": "string",
            "description": "需要制定计划的任务或问题描述",
        },
        "steps": {
            "type": "array",
            "description": "研究计划步骤列表",
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "步骤唯一标识（如 step1, step2）",
                    },
                    "description": {
                        "type": "string",
                        "description": "该步骤要研究或完成的内容描述",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "completed"],
                        "description": "当前状态",
                    },
                },
                "required": ["id", "description", "status"],
            },
        },
    },
    "required": ["steps"],
}


# ── 网络工具 ──

WEB_SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "搜索关键词，与搜索引擎的用法一致",
        },
        "max_results": {
            "type": "integer",
            "description": "返回的最大结果数，默认 5，范围 1-10",
            "default": 5,
        },
    },
    "required": ["query"],
}

WEB_FETCH_SCHEMA = {
    "type": "object",
    "properties": {
        "url": {
            "type": "string",
            "description": "要抓取的网页 URL（来自 web_search 结果或用户提供）",
        },
        "title": {
            "type": "string",
            "description": "保存到知识库时使用的文档标题，不填则自动从网页 <title> 提取",
        },
    },
    "required": ["url"],
}


# ── 数据分析工具 ──

DATA_SCHEMA_SCHEMA = {
    "type": "object",
    "properties": {
        "doc_id": {
            "type": "integer",
            "description": "要查看结构的表格文档 ID（type=spreadsheet 或 csv）",
        },
    },
    "required": ["doc_id"],
}

DATA_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "doc_id": {
            "type": "integer",
            "description": "要分析的表格文档 ID",
        },
        "sql": {
            "type": "string",
            "description": (
                "要执行的 SQL 查询语句（仅支持 SELECT）。"
                "表名为 t，列名来自 data_schema 返回的 columns.name。"
                "例如: SELECT city, AVG(price) FROM t GROUP BY city"
            ),
        },
    },
    "required": ["doc_id", "sql"],
}


# ── Skills 工具 ──

READ_SKILL_SCHEMA = {
    "type": "object",
    "properties": {
        "skill_name": {
            "type": "string",
            "description": "要加载的技能名称（来自系统提示词中列出的 Available Skills）",
        },
        "file_path": {
            "type": "string",
            "description": "可选。读取技能目录下的特定文件路径（相对路径）",
        },
    },
    "required": ["skill_name"],
}

EXECUTE_SKILL_SCRIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "skill_name": {
            "type": "string",
            "description": "技能名称",
        },
        "script_path": {
            "type": "string",
            "description": "要执行的脚本相对路径，如 scripts/analyze.py",
        },
        "input": {
            "type": "string",
            "description": "通过 stdin 传给脚本的输入数据（JSON 字符串）",
        },
        "args": {
            "type": "array",
            "items": {"type": "string"},
            "description": "命令行参数，如 [\"--type\", \"numeric\"]",
        },
    },
    "required": ["skill_name", "script_path"],
}


# ── 知识检索工具 ──

SEMANTIC_SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "queries": {
            "type": "array",
            "description": (
                "1-5 个语义查询语句。将用户的复杂问题拆解为多个独立的语义查询, "
                "每个查询应是一个完整的、自包含的问题或概念描述。 "
                "例如用户问 RAG 的实现原理和优缺点, 可拆为 "
                '["RAG 实现原理", "RAG 优缺点", "RAG 技术架构"]'
            ),
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 5,
        },
        "top_k": {
            "type": "integer",
            "description": "每个查询返回的最大结果数，默认 5，范围 1-10",
            "default": 5,
        },
    },
    "required": ["queries"],
}

KEYWORD_SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": (
                "一个精确的关键词搜索表达式。支持多个关键词用空格分隔（AND 逻辑），"
                "如 \u201c2024 年度 财务 报告\u201d。适用于查找特定术语、编号、人名、地名等。"
            ),
        },
        "top_k": {
            "type": "integer",
            "description": "返回的最大结果数，默认 10，范围 1-20",
            "default": 10,
        },
    },
    "required": ["query"],
}

GET_CHUNKS_SCHEMA = {
    "type": "object",
    "properties": {
        "doc_id": {
            "type": "integer",
            "description": "要获取分块内容的文档 ID",
        },
        "limit": {
            "type": "integer",
            "description": "最多返回的分块数，默认 20",
            "default": 20,
        },
    },
    "required": ["doc_id"],
}

GET_DOC_INFO_SCHEMA = {
    "type": "object",
    "properties": {
        "doc_id": {
            "type": "integer",
            "description": "要查看元数据的文档 ID",
        },
    },
    "required": ["doc_id"],
}


# ── 文件操作工具（已有，从 ai_service.py 迁出） ──

SEARCH_DOCS_SCHEMA = {
    "type": "object",
    "properties": {
        "keyword": {
            "type": "string",
            "description": "搜索关键词",
        },
        "size": {
            "type": "integer",
            "description": "返回结果数量，默认 20",
            "default": 20,
        },
    },
    "required": ["keyword"],
}

CREATE_DOC_DIR_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "description": "目录名称",
        },
        "parent_id": {
            "type": "integer",
            "description": "父目录 ID，不填则创建为顶级目录",
        },
    },
    "required": ["name"],
}

MOVE_DOCS_TO_DIR_SCHEMA = {
    "type": "object",
    "properties": {
        "doc_ids": {
            "type": "array",
            "items": {"type": "integer"},
            "description": "要移动的文档 ID 列表",
        },
        "dir_id": {
            "type": "integer",
            "description": "目标目录 ID",
        },
    },
    "required": ["doc_ids", "dir_id"],
}

CREATE_TEXT_DOC_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "文档标题",
        },
        "content": {
            "type": "string",
            "description": "文档正文内容",
        },
        "doc_dir_id": {
            "type": "integer",
            "description": "所属目录 ID，不填则放在根目录",
        },
    },
    "required": ["title", "content"],
}

CREATE_SPREADSHEET_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "表格标题",
        },
        "headers": {
            "type": "array",
            "items": {"type": "string"},
            "description": '列名列表，如 ["姓名", "金额", "日期"]',
        },
        "rows": {
            "type": "array",
            "items": {
                "type": "array",
                "description": "一行数据，顺序与 headers 对应",
            },
            "description": "数据行列表，每行为与 headers 顺序对应的值数组",
        },
        "doc_dir_id": {
            "type": "integer",
            "description": "所属目录 ID，不填则放在根目录",
        },
    },
    "required": ["title", "headers", "rows"],
}

LIST_DIRS_SCHEMA = {
    "type": "object",
    "properties": {},
    "required": [],
}

GET_DOC_CONTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "doc_id": {
            "type": "integer",
            "description": "文档 ID",
        },
    },
    "required": ["doc_id"],
}

FIND_UNCLASSIFIED_DOCS_SCHEMA = {
    "type": "object",
    "properties": {
        "size": {
            "type": "integer",
            "description": "返回数量上限，默认 20",
            "default": 20,
        },
    },
    "required": [],
}

TAG_DOC_SCHEMA = {
    "type": "object",
    "properties": {
        "doc_id": {
            "type": "integer",
            "description": "文档 ID",
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "description": '标签名称列表，如 ["财务", "2024"]，会覆盖原有标签',
        },
    },
    "required": ["doc_id", "tags"],
}

CREATE_PPT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "PPT 文件标题",
        },
        "slides": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "幻灯片标题"},
                    "content": {"type": "string", "description": "幻灯片正文内容"},
                },
                "required": ["title", "content"],
            },
            "description": "幻灯片列表，每项包含 title 和 content",
        },
        "doc_dir_id": {
            "type": "integer",
            "description": "所属目录 ID，不填则放在根目录",
        },
    },
    "required": ["title", "slides"],
}


# ── 工具注册清单 ──
# 格式：(工具名称, 描述, JSON Schema, 所需能力)

ALL_TOOL_DEFS = [
    # ── 思考与规划 ──
    {
        "name": TOOL_THINKING,
        "description": (
            "动态反思式思考工具，用于分析复杂问题。\n\n"
            "## 何时使用\n"
            "需要拆解复杂问题、多步骤推理、分析过程中需要调整方向时使用。\n"
            "调用本工具记录每一步思考，直到得出结论（next_thought_needed=false）。\n\n"
            "## 关键规则\n"
            "- thought 用自然语言写，不要提及工具名称，描述你要发现什么、为什么\n"
            "- 思考完成后，用普通文本回复输出最终答案（不要再调用任何工具）\n"
            "- 绝不要把最终答案直接放在 thought 里\n"
            "- thought_number/total_thoughts 可动态调整，不必一开始就估准\n\n"
            "## 最佳实践\n"
            "1. 先用 1-2 步分析问题本质\n"
            "2. 中间步骤可以穿插工具调用（搜索→分析→再搜索→反思）\n"
            "3. 发现之前的思考有误时，用 is_revision=true 修正\n"
            "4. 需要探索多条路径时，用 branch_from_thought 分支\n"
            "5. 完成全部思考后，用普通文本回复交付最终答案"
        ),
        "parameters": THINKING_SCHEMA,
        "caps": set(),
    },
    {
        "name": TOOL_TODO_WRITE,
        "description": (
            "创建和管理检索/研究任务的计划清单。\n\n"
            "## 核心规则\n"
            "- **仅用于检索和研究任务**（搜索知识库、获取文档、收集信息）\n"
            "- **不要**包含总结、综合、写回答等任务——那些用 thinking 工具\n"
            "- 同时只有一个步骤 in_progress，完成后立即标记 completed\n\n"
            "## 何时使用\n"
            "1. 用户的问题需要 3+ 步检索才能完整回答\n"
            "2. 用户明确要求列出计划\n"
            "3. 用户提供了多个任务/问题\n"
            "4. 在开始每个步骤前标记 in_progress，完成后标记 completed\n\n"
            "## 何时不用\n"
            "- 单个简单问题一步就能回答\n"
            "- 纯对话/闲聊\n"
            "- 不需要检索的总结类任务\n\n"
            "## 状态说明\n"
            "- pending：尚未开始\n"
            "- in_progress：正在执行（同时只有一个）\n"
            "- completed：已完成\n\n"
            "完成所有检索步骤后，用 thinking 工具综合发现。"
        ),
        "parameters": TODO_WRITE_SCHEMA,
        "caps": set(),
    },
    # ── 知识检索 ──
    {
        "name": TOOL_SEMANTIC_SEARCH,
        "description": (
            "语义/向量检索工具，按含义而非关键词查找知识库内容。"
            "适用于概念性问题、解释性查询、话题探索。"
            "输入 1-5 个语义查询语句，返回按相关性排序的文档分块。"
            "在语义搜索后，应用 keyword_search 补充精确匹配，用 get_chunks 展开全文。"
        ),
        "parameters": SEMANTIC_SEARCH_SCHEMA,
        "caps": {"vector"},
    },
    {
        "name": TOOL_KEYWORD_SEARCH,
        "description": (
            "关键词全文检索工具，精确匹配特定术语、编号、人名、地名等。"
            "适用于查找包含特定关键词的文档分块。"
            "支持多个关键词空格分隔（AND 逻辑）。"
            "先用语义搜索理解大意，再用本工具精确命中具体细节。"
        ),
        "parameters": KEYWORD_SEARCH_SCHEMA,
        "caps": {"keyword"},
    },
    {
        "name": TOOL_GET_CHUNKS,
        "description": (
            "获取指定文档的所有分块完整内容。"
            "当搜索返回某个文档的片段后，用此工具展开该文档的完整上下文。"
            "参数 doc_id 来自搜索结果的 doc_id 字段。"
        ),
        "parameters": GET_CHUNKS_SCHEMA,
        "caps": set(),
    },
    {
        "name": TOOL_GET_DOC_INFO,
        "description": (
            "查看文档元数据：标题、类型、标签、创建时间、所属目录、内容摘要。"
            "在决定是否深入阅读某个文档前，先查看其元数据判断相关性。"
        ),
        "parameters": GET_DOC_INFO_SCHEMA,
        "caps": set(),
    },
    # ── 网络工具 ──
    {
        "name": TOOL_WEB_SEARCH,
        "description": (
            "搜索引擎检索，搜索互联网获取最新信息。\n"
            "适用于知识库中找不到的实时信息、新闻事件、最新动态。\n"
            "返回结果的标题、URL 和摘要，可用 web_fetch 进一步抓取全文。"
        ),
        "parameters": WEB_SEARCH_SCHEMA,
        "caps": set(),
    },
    {
        "name": TOOL_WEB_FETCH,
        "description": (
            "抓取网页内容并保存到知识库。\n"
            "从 web_search 结果中选择相关 URL，抓取全文转为纯文本，\n"
            "自动保存为文档（type=html），后续可通过 semantic_search / keyword_search 检索。\n"
            "参数 url 应来自 web_search 返回结果。"
        ),
        "parameters": WEB_FETCH_SCHEMA,
        "caps": set(),
    },
    # ── 数据分析 ──
    {
        "name": TOOL_DATA_SCHEMA,
        "description": (
            "查看表格文档的结构信息：列名、数据类型、样例值、总行数。\n"
            "在执行 data_analysis 之前，必须先调用本工具了解表结构。\n"
            "参数 doc_id 来自搜索结果的 doc_id 字段（文档 type 须为 spreadsheet 或 csv）。"
        ),
        "parameters": DATA_SCHEMA_SCHEMA,
        "caps": set(),
    },
    {
        "name": TOOL_DATA_ANALYSIS,
        "description": (
            "对表格文档执行 SQL 查询（DuckDB 驱动）。\n"
            "仅支持 SELECT / SHOW / DESCRIBE，拒绝 INSERT/UPDATE/DELETE 等写操作。\n"
            "表固定命名为 t，列名来自 data_schema 返回的 columns.name。\n"
            "SQL 示例: SELECT 城市, AVG(金额) FROM t GROUP BY 城市 ORDER BY AVG(金额) DESC\n"
            "查询前请先用 data_schema 了解表结构。"
        ),
        "parameters": DATA_ANALYSIS_SCHEMA,
        "caps": set(),
    },
    # ── Skills 系统 ──
    {
        "name": TOOL_READ_SKILL,
        "description": (
            "按需加载技能的完整指令（渐进式披露 Level 2）。\n"
            "系统提示词中列出了可用技能的名称和简介，当你需要执行某个技能时，"
            "先调用本工具加载其完整指令（步骤、脚本、最佳实践等）。\n"
            "参数 skill_name 来自系统提示词中 Available Skills 列表。"
        ),
        "parameters": READ_SKILL_SCHEMA,
        "caps": set(),
    },
    {
        "name": TOOL_EXECUTE_SKILL_SCRIPT,
        "description": (
            "执行技能目录中的 Python 脚本（渐进式披露 Level 3）。\n"
            "先通过 read_skill 了解可用脚本和用法，再调用本工具执行。\n"
            "- input: 通过 stdin 传入的数据（JSON 字符串）\n"
            "- args: 命令行参数，如 [\"--type\", \"numeric\"]\n"
            "脚本在技能目录中执行，超时 60 秒。"
        ),
        "parameters": EXECUTE_SKILL_SCRIPT_SCHEMA,
        "caps": set(),
    },
    # ── 文件操作（已有） ──
    {
        "name": TOOL_SEARCH_DOCS,
        "description": "全文检索文档库，根据关键词搜索相关文件，返回匹配的文档列表（含 doc_id 和标题）",
        "parameters": SEARCH_DOCS_SCHEMA,
        "caps": {"keyword"},
    },
    {
        "name": TOOL_CREATE_DOC_DIR,
        "description": "创建一个新的目录，返回新目录的 dir_id",
        "parameters": CREATE_DOC_DIR_SCHEMA,
        "caps": set(),
    },
    {
        "name": TOOL_MOVE_DOCS_TO_DIR,
        "description": "将指定的文档移动到某个目录",
        "parameters": MOVE_DOCS_TO_DIR_SCHEMA,
        "caps": set(),
    },
    {
        "name": TOOL_CREATE_TEXT_DOC,
        "description": "创建一篇文本文档，内容保存到知识库并建立全文检索索引",
        "parameters": CREATE_TEXT_DOC_SCHEMA,
        "caps": set(),
    },
    {
        "name": TOOL_CREATE_SPREADSHEET,
        "description": "创建一张表格文档，支持多行多列结构化数据",
        "parameters": CREATE_SPREADSHEET_SCHEMA,
        "caps": set(),
    },
    {
        "name": TOOL_LIST_DIRS,
        "description": "获取所有文档目录的树形结构，返回 id、名称、父目录、子目录列表。在做整理操作前应先调用此工具了解现有目录结构",
        "parameters": LIST_DIRS_SCHEMA,
        "caps": set(),
    },
    {
        "name": TOOL_GET_DOC_CONTENT,
        "description": "获取指定文档的详细信息，包括标题、类型、内容摘要、标签、所属目录",
        "parameters": GET_DOC_CONTENT_SCHEMA,
        "caps": set(),
    },
    {
        "name": TOOL_FIND_UNCLASSIFIED_DOCS,
        "description": "查找尚未归入任何目录的文档，用于治理检查和批量归档",
        "parameters": FIND_UNCLASSIFIED_DOCS_SCHEMA,
        "caps": set(),
    },
    {
        "name": TOOL_TAG_DOC,
        "description": "为文档设置标签（覆盖写，传入完整标签列表）",
        "parameters": TAG_DOC_SCHEMA,
        "caps": set(),
    },
    {
        "name": TOOL_CREATE_PPT,
        "description": "创建一份 PPT 演示文稿，每页包含标题和正文内容",
        "parameters": CREATE_PPT_SCHEMA,
        "caps": set(),
    },
]
