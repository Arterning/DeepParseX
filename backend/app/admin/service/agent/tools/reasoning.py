"""
思考与规划工具执行函数

对应 WeKnora 的 sequentialthinking.go 和 todo_write.go。

thinking 工具：记录结构化思考步骤，帮助 LLM "慢思考"。
- 每次调用记录一步思考，LLM 循环调用直到 next_thought_needed=false
- 工具只做验证和格式化，不持久化状态
- 返回结构化数据让 LLM 在下轮看到自己的思考历史

todo_write 工具：创建和管理检索任务计划。
- 适合 3+ 步的复杂检索任务
- 用 emoji 状态标记：⏳ pending / 🔄 in_progress / ✅ completed
"""
from backend.common.log import log


async def execute_thinking(
    thought: str,
    next_thought_needed: bool,
    thought_number: int,
    total_thoughts: int,
    is_revision: bool = False,
    revises_thought: int = None,
    branch_from_thought: int = None,
    branch_id: str = "",
    needs_more_thoughts: bool = False,
) -> dict:
    """
    执行 thinking 工具——记录一步结构化思考。

    对应 WeKnora SequentialThinkingTool.Execute。
    """
    if not thought or not thought.strip():
        return {"error": "thought 不能为空"}

    if thought_number < 1:
        return {"error": f"thought_number 必须 >= 1，收到 {thought_number}"}

    # 动态调整 total_thoughts
    if thought_number > total_thoughts:
        total_thoughts = thought_number

    incomplete = next_thought_needed or needs_more_thoughts or thought_number < total_thoughts

    output = "思考已记录"
    if incomplete:
        output += " — 还有未完成的步骤，请继续探索"

    return {
        "thought_number": thought_number,
        "total_thoughts": total_thoughts,
        "next_thought_needed": next_thought_needed,
        "incomplete_steps": incomplete,
        "thought": thought,
        "output": output,
    }


async def execute_todo_write(
    steps: list[dict],
    task: str = "",
) -> dict:
    """
    执行 todo_write 工具——创建/更新检索任务计划。

    对应 WeKnora TodoWriteTool.Execute。
    """
    if not steps:
        return {"error": "steps 不能为空"}

    if not task:
        task = "检索研究任务"

    # 统计
    total = len(steps)
    completed = sum(1 for s in steps if s.get("status") == "completed")
    in_progress_count = sum(1 for s in steps if s.get("status") == "in_progress")
    pending = sum(1 for s in steps if s.get("status") == "pending")

    # 状态图标映射
    status_icons = {
        "pending": "⏳",
        "in_progress": "🔄",
        "completed": "✅",
    }

    # 构建格式化的 Markdown 输出
    lines = [f"## {task}", ""]
    for s in steps:
        sid = s.get("id", "?")
        desc = s.get("description", "")
        status = s.get("status", "pending")
        icon = status_icons.get(status, "❓")
        lines.append(f"{icon} **{sid}**: {desc}")

    lines.append("")
    lines.append(f"---")
    lines.append(f"📊 进度: {completed}/{total} 完成")
    if in_progress_count > 0:
        lines.append(f"🔄 {in_progress_count} 个进行中")
    if pending > 0:
        lines.append(f"⏳ {pending} 个待处理")
    lines.append("")
    lines.append("💡 提示: 完成所有检索步骤后，用 thinking 工具综合发现。")

    output = "\n".join(lines)

    return {
        "task": task,
        "total_steps": total,
        "completed": completed,
        "in_progress": in_progress_count,
        "pending": pending,
        "plan_created": True,
        "output": output,
    }
