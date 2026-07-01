"""
Agent ReAct 循环

对应 WeKnora 的 engine.go — AgentEngine.executeLoop：
- Think：LLM 调用
- Act：工具执行（通过 ToolRegistry）
- Observe：结果追加到消息上下文

两种模式：
1. run()          — 阻塞模式，返回最终答案（兼容旧接口）
2. run_stream()   — 流式模式，yield SSE 事件供前端实时展示
"""
import json
import asyncio
import requests
from typing import Optional, AsyncGenerator

from backend.common.log import log
from backend.app.admin.service.config_service import config_service
from backend.app.admin.service.agent.tool_registry import ToolRegistry, create_default_registry


# 默认最大工具调用轮次（对应 WeKnora DefaultAgentMaxIterations = 20）
DEFAULT_MAX_TOOL_ROUNDS = 20


# ── 工具结果摘要规则 ──
# 不同工具产生的摘要格式，用于前端 tool_result 事件展示

def _summarize_result(tool_name: str, result_str: str) -> str:
    """从工具返回的 JSON 字符串提取简短摘要"""
    try:
        data = json.loads(result_str)
    except json.JSONDecodeError:
        return "执行完成"

    if "error" in data:
        return f"执行出错: {str(data['error'])[:80]}"

    if tool_name == "semantic_search":
        total = data.get("total", 0)
        return f"语义搜索返回 {total} 条结果"

    if tool_name == "keyword_search":
        total = data.get("total", 0)
        return f"关键词搜索返回 {total} 条结果"

    if tool_name == "get_chunks":
        total = data.get("total_chunks", 0)
        return f"获取文档分块 {total} 个"

    if tool_name == "get_doc_info":
        title = data.get("title", "")
        return f"文档信息: {title[:40]}"

    if tool_name == "web_search":
        total = data.get("total", 0)
        return f"网络搜索返回 {total} 条结果"

    if tool_name == "web_fetch":
        if data.get("success"):
            title = data.get("title", "")
            return f"已抓取网页: {title[:40]}"
        return "网页抓取失败"

    if tool_name == "thinking":
        step = data.get("thought_number", "?")
        total = data.get("total_thoughts", "?")
        return f"思考步骤 {step}/{total}"

    if tool_name == "todo_write":
        total = data.get("total_steps", 0)
        completed = data.get("completed", 0)
        return f"计划: {completed}/{total} 已完成"

    if tool_name == "data_schema":
        total = data.get("total_rows", 0)
        cols = len(data.get("columns", []))
        return f"表格结构: {cols} 列, {total} 行"

    if tool_name == "data_analysis":
        total = data.get("total_rows", 0)
        return f"SQL 查询返回 {total} 行"

    # MCP 工具
    if tool_name.startswith("mcp_"):
        if data.get("success"):
            server = data.get("server", "unknown")
            return f"[{server}] 执行成功"
        return f"MCP 工具执行失败"

    # 文件操作工具
    if data.get("success"):
        return "操作成功"
    return "执行完成"


def _format_sse(event: str, data: dict) -> str:
    """格式化一条 SSE 消息"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


class AgentEngine:
    """
    Agent 引擎——负责 ReAct 循环。

    使用方式：
        registry = create_default_registry()
        engine = AgentEngine(registry)
        answer = await engine.run(
            messages=[{"role": "user", "content": "什么是RAG？"}],
            system_prompt="你是一个助手...",
        )
    """

    def __init__(self, tool_registry: Optional[ToolRegistry] = None):
        self.registry = tool_registry or create_default_registry()

    async def run(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
        config: Optional[dict] = None,
        max_tool_rounds: int = DEFAULT_MAX_TOOL_ROUNDS,
    ) -> str:
        """
        执行 Agent 对话。

        Args:
            messages: 对话消息列表 [{"role": "user", "content": "..."}, ...]
            system_prompt: 系统提示词
            config: 可选配置 {"llm": {"temperature": 0.2}}
            max_tool_rounds: 最大工具调用轮次

        Returns:
            LLM 最终文本回复
        """
        merged_settings = await config_service.get_merged_settings()

        temperature = 0.2
        if config:
            temperature = config.get("llm", {}).get("temperature", temperature)

        # 构建完整消息列表
        all_messages = []
        if system_prompt:
            all_messages.append({"role": "system", "content": system_prompt})
        all_messages.extend(messages)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {merged_settings.LLM_API_KEY}",
        }
        tools = self.registry.get_definitions()

        loop = asyncio.get_running_loop()

        for round_idx in range(max_tool_rounds):
            payload = {
                "model": merged_settings.LLM_MODEL,
                "temperature": temperature,
                "messages": all_messages,
                "tools": tools,
                "tool_choice": "auto",
            }

            response = await loop.run_in_executor(
                None,
                lambda p=payload: requests.post(
                    merged_settings.LLM_API_URL, headers=headers, json=p
                ),
            )

            if response.status_code != 200:
                raise Exception(f"API request failed: {response.text}")

            resp_data = response.json()
            choice = resp_data["choices"][0]
            assistant_message = choice["message"]
            finish_reason = choice.get("finish_reason", "stop")

            # 将 assistant 消息加入上下文
            all_messages.append(assistant_message)

            # 检查是否有工具调用
            if finish_reason == "tool_calls" and assistant_message.get("tool_calls"):
                for tool_call in assistant_message["tool_calls"]:
                    tool_name = tool_call["function"]["name"]
                    try:
                        tool_args = json.loads(tool_call["function"]["arguments"])
                    except json.JSONDecodeError:
                        tool_args = {}

                    log.info(
                        f"[AgentEngine] round={round_idx + 1} 调用工具: {tool_name}"
                    )
                    log.debug(f"[AgentEngine] 工具参数: {json.dumps(tool_args, ensure_ascii=False)[:300]}")

                    tool_result = await self.registry.execute(tool_name, tool_args)
                    log.debug(f"[AgentEngine] 工具结果长度: {len(tool_result)} 字符")

                    # 追加 tool result 消息
                    all_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": tool_result,
                    })
            else:
                # 无工具调用，返回最终文本
                return assistant_message.get("content") or ""

        # 超限优雅降级：让 LLM 基于已有工具结果总结最终回答
        # 对应 WeKnora handleMaxIterations（finalize.go:150）
        log.warning(f"[AgentEngine] 达到最大轮次 {max_tool_rounds}，请求 LLM 基于已有结果总结")
        all_messages.append({
            "role": "user",
            "content": (
                "已达到最大工具调用次数上限。"
                "请基于以上所有检索结果，用一个完整的回答来总结你对用户问题的发现。"
                "如果多次搜索都未找到相关信息，请诚实告知。"
            ),
        })

        payload = {
            "model": merged_settings.LLM_MODEL,
            "temperature": temperature,
            "messages": all_messages,
        }

        response = await loop.run_in_executor(
            None,
            lambda p=payload: requests.post(
                merged_settings.LLM_API_URL, headers=headers, json=p
            ),
        )

        if response.status_code == 200:
            resp_data = response.json()
            return resp_data["choices"][0]["message"].get("content") or ""

        raise Exception(f"AgentEngine 超出最大工具调用轮次 ({max_tool_rounds})")

    async def run_stream(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
        config: Optional[dict] = None,
        max_tool_rounds: int = DEFAULT_MAX_TOOL_ROUNDS,
    ) -> AsyncGenerator[str, None]:
        """
        流式执行 Agent 对话，yield SSE 格式事件字符串。

        事件类型：
        - status:  {"type": "start"|"done"|"max_rounds"}
        - tool_call: {"name": "...", "args": {...}, "round": N}
        - thought: {"content": "...", "step": N, "total": N}
        - tool_result: {"name": "...", "success": bool, "summary": "..."}
        - answer: {"content": "..."}

        Yields:
            SSE 格式字符串: "event: <type>\\ndata: <json>\\n\\n"
        """
        merged_settings = await config_service.get_merged_settings()

        temperature = 0.2
        if config:
            temperature = config.get("llm", {}).get("temperature", temperature)

        all_messages = []
        if system_prompt:
            all_messages.append({"role": "system", "content": system_prompt})
        all_messages.extend(messages)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {merged_settings.LLM_API_KEY}",
        }
        tools = self.registry.get_definitions()
        loop = asyncio.get_running_loop()

        yield _format_sse("status", {"type": "start"})

        for round_idx in range(max_tool_rounds):
            payload = {
                "model": merged_settings.LLM_MODEL,
                "temperature": temperature,
                "messages": all_messages,
                "tools": tools,
                "tool_choice": "auto",
            }

            response = await loop.run_in_executor(
                None,
                lambda p=payload: requests.post(
                    merged_settings.LLM_API_URL, headers=headers, json=p
                ),
            )

            if response.status_code != 200:
                yield _format_sse("status", {"type": "error", "message": f"API error: {response.status_code}"})
                return

            resp_data = response.json()
            choice = resp_data["choices"][0]
            assistant_message = choice["message"]
            finish_reason = choice.get("finish_reason", "stop")

            all_messages.append(assistant_message)

            if finish_reason == "tool_calls" and assistant_message.get("tool_calls"):
                for tool_call in assistant_message["tool_calls"]:
                    tool_name = tool_call["function"]["name"]
                    try:
                        tool_args = json.loads(tool_call["function"]["arguments"])
                    except json.JSONDecodeError:
                        tool_args = {}

                    # ── 发送 tool_call 事件 ──
                    yield _format_sse("tool_call", {
                        "name": tool_name,
                        "args": tool_args,
                        "round": round_idx + 1,
                    })

                    # ── thinking 工具特殊处理：发送 thought 事件 ──
                    if tool_name == "thinking":
                        thought_content = tool_args.get("thought", "")
                        thought_num = tool_args.get("thought_number", 1)
                        thought_total = tool_args.get("total_thoughts", 1)
                        yield _format_sse("thought", {
                            "content": thought_content,
                            "step": thought_num,
                            "total": thought_total,
                        })

                    # 执行工具
                    tool_result = await self.registry.execute(tool_name, tool_args)
                    summary = _summarize_result(tool_name, tool_result)

                    # ── 发送 tool_result 事件 ──
                    yield _format_sse("tool_result", {
                        "name": tool_name,
                        "success": "error" not in tool_result[:50].lower(),
                        "summary": summary,
                    })

                    all_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": tool_result,
                    })
            else:
                # 无工具调用 → 最终答案
                final_answer = assistant_message.get("content") or ""
                yield _format_sse("answer", {"content": final_answer})
                yield _format_sse("status", {"type": "done"})
                return

        # 超限优雅降级
        log.warning(f"[AgentEngine] 达到最大轮次 {max_tool_rounds}，请求 LLM 总结")
        yield _format_sse("status", {"type": "max_rounds", "message": f"达到最大轮次 {max_tool_rounds}，正在总结已有结果..."})

        all_messages.append({
            "role": "user",
            "content": (
                "已达到最大工具调用次数上限。"
                "请基于以上所有检索结果，用一个完整的回答来总结你对用户问题的发现。"
                "如果多次搜索都未找到相关信息，请诚实告知。"
            ),
        })

        payload = {
            "model": merged_settings.LLM_MODEL,
            "temperature": temperature,
            "messages": all_messages,
        }

        response = await loop.run_in_executor(
            None,
            lambda p=payload: requests.post(
                merged_settings.LLM_API_URL, headers=headers, json=p
            ),
        )

        if response.status_code == 200:
            resp_data = response.json()
            final_answer = resp_data["choices"][0]["message"].get("content") or ""
            yield _format_sse("answer", {"content": final_answer})
            yield _format_sse("status", {"type": "done"})
            return

        yield _format_sse("status", {"type": "error", "message": "总结请求失败"})


# 便捷函数：直接用默认 registry 运行
async def run_agent(
    messages: list[dict],
    system_prompt: Optional[str] = None,
    config: Optional[dict] = None,
    max_tool_rounds: int = DEFAULT_MAX_TOOL_ROUNDS,
) -> str:
    """使用默认工具注册运行 Agent（便捷入口）"""
    engine = AgentEngine()
    return await engine.run(
        messages=messages,
        system_prompt=system_prompt,
        config=config,
        max_tool_rounds=max_tool_rounds,
    )


async def run_agent_stream(
    messages: list[dict],
    system_prompt: Optional[str] = None,
    config: Optional[dict] = None,
    max_tool_rounds: int = DEFAULT_MAX_TOOL_ROUNDS,
) -> AsyncGenerator[str, None]:
    """使用默认工具注册流式运行 Agent（便捷入口）"""
    engine = AgentEngine()
    async for event in engine.run_stream(
        messages=messages,
        system_prompt=system_prompt,
        config=config,
        max_tool_rounds=max_tool_rounds,
    ):
        yield event
