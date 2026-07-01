"""
Agent system prompt 构建

对应 WeKnora 的 prompts.go — BuildSystemPromptWithOptions。
只维护一份提示词，聚焦工作流程策略，不枚举具体工具名。
"""
from backend.common.log import log


# 全局唯一的 Agent system prompt
AGENT_SYSTEM_PROMPT = """你是一个知识库助手，拥有检索、分析、操作等多种工具。

## 核心原则

1. **先查后答**：回答知识性问题前，必须先检索知识库（语义搜索 + 关键词搜索互补）
2. **用工具，不用猜**：不确定时用工具查，不要凭空编造
3. **标注来源**：引用信息时说明来自哪个文档

## 工作策略

- 概念性/解释性问题 → 语义搜索把握方向
- 精确术语/编号/人名 → 关键词搜索精准命中
- 搜索结果不足 → 换角度、换关键词重试
- 找到相关文档 → 展开全文了解上下文
- 表格数据 → 先查结构再写 SQL 分析
- 复杂多步任务 → 用计划工具先规划再执行

## 回答风格

- 准确、简洁、有条理
- 知识库查不到的诚实告知，不编造
- 来源标注格式："来自《文档名》"
"""


def format_skills_prompt(metadata_list: list) -> str:
    """
    将技能元数据格式化为 system prompt 中的 Skills 块（Level 1 渐进式披露）。

    对应 WeKnora prompts.go formatSkillsMetadata()。
    """
    if not metadata_list:
        return ""

    lines = [
        "",
        "### 可用技能 (Available Skills)",
        "",
        "系统提供了以下专业技能。当你需要执行复杂的数据处理、格式转换、"
        "信息提取等任务时，请先调用 read_skill 加载技能指令，再按指令操作。",
        "",
    ]
    for i, meta in enumerate(metadata_list, 1):
        lines.append(f"{i}. **{meta.name}** — {meta.description}")

    lines.append("")
    lines.append("**工具**: read_skill(skill_name) 加载技能指令; execute_skill_script(skill_name, script_path, input, args) 执行脚本")
    lines.append("")

    return "\n".join(lines)


def build_agent_system_prompt(skills_metadata: list | None = None) -> str:
    """构建 Agent 模式的 system prompt"""
    prompt = AGENT_SYSTEM_PROMPT
    if skills_metadata:
        prompt += format_skills_prompt(skills_metadata)
    return prompt
