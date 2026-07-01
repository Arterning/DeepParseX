"""
工具注册中心

对应 WeKnora 的 tools/registry.go — ToolRegistry：
- RegisterTool：first-wins 注册，防止同名覆盖
- get_definitions：返回给 LLM 的 OpenAI function-calling 格式
- execute：执行工具 → JSON 序列化 → 截断输出

设计借鉴 WeKnora：
- 工具定义与执行分离（ToolDef.execute 是 Callable）
- 输出自动截断（MAX_OUTPUT_CHARS），防止撑爆 context
- 执行错误时返回可读的错误信息
"""
import json
from typing import Optional

from backend.common.log import log
from backend.app.admin.service.agent.tools.base import ToolDef

# 工具输出最大字符数（对应 WeKnora 的 maxToolOutputSize）
MAX_OUTPUT_CHARS = 4000


class ToolRegistry:
    """工具注册中心"""

    def __init__(self):
        self._tools: dict[str, ToolDef] = {}

    def register(self, tool: ToolDef) -> None:
        """
        注册工具。first-wins 策略：同名工具不覆盖。
        对应 WeKnora ToolRegistry.RegisterTool。
        """
        if tool.name in self._tools:
            log.warning(f"[ToolRegistry] 工具 '{tool.name}' 已注册，跳过（first-wins）")
            return
        self._tools[tool.name] = tool
        log.debug(f"[ToolRegistry] 注册工具: {tool.name}")

    def get(self, name: str) -> Optional[ToolDef]:
        return self._tools.get(name)

    def register_mcp_tool(self, mcp_tool) -> None:
        """
        注册 MCP 工具（MCPToolDef → ToolDef 转换 + 注册）。

        MCP 工具符合 ToolDef 接口（name/description/parameters/execute），
        直接转为 ToolDef 注册。
        """
        tool = ToolDef(
            name=mcp_tool.name,
            description=mcp_tool.description,
            parameters=mcp_tool.parameters,
            execute=mcp_tool.execute,
            required_caps=mcp_tool.required_caps,
        )
        self.register(tool)

    def get_definitions(self) -> list[dict]:
        """
        返回所有已注册工具的 OpenAI function-calling 格式定义。
        按名称排序以保证跨请求 JSON 稳定（对应 WeKnora 的 prompt caching 兼容）。
        """
        return [
            tool.to_openai_tool()
            for _, tool in sorted(self._tools.items(), key=lambda x: x[0])
        ]

    async def execute(self, name: str, args: dict) -> str:
        """
        执行工具并返回 JSON 字符串结果。

        流程（对应 WeKnora ExecuteTool）：
        1. 查找工具
        2. 调用 execute(**args)
        3. JSON 序列化
        4. 截断超长输出

        Returns:
            JSON 字符串格式的工具结果
        """
        tool = self._tools.get(name)
        if tool is None:
            error_result = json.dumps({"error": f"Unknown tool: {name}"}, ensure_ascii=False)
            log.warning(f"[ToolRegistry] 未知工具: {name}")
            return error_result

        try:
            result: dict = await tool.execute(**args)
            result_str = json.dumps(result, ensure_ascii=False)

            # 输出截断（对应 WeKnora TruncateToolOutput）
            if len(result_str) > MAX_OUTPUT_CHARS:
                result_str = result_str[:MAX_OUTPUT_CHARS] + "\n...[截断，结果过长]"
                log.info(f"[ToolRegistry] 工具 '{name}' 输出截断: {len(result_str)} -> {MAX_OUTPUT_CHARS}")

            return result_str

        except TypeError as e:
            log.error(f"[ToolRegistry] 工具 '{name}' 参数错误: {repr(e)}, 收到 args={args}")
            return json.dumps({"error": f"参数错误: {str(e)}"}, ensure_ascii=False)
        except Exception as e:
            log.error(f"[ToolRegistry] 工具 '{name}' 执行失败: {repr(e)}")
            return json.dumps({"error": repr(e)}, ensure_ascii=False)


def create_default_registry() -> ToolRegistry:
    """
    创建注册了所有 13 个工具的 ToolRegistry。

    对应 WeKnora agent_service.go 的 registerTools()。
    所有工具在此一次性注册，未来可按能力过滤。
    """
    from backend.app.admin.service.agent.tools.definitions import ALL_TOOL_DEFS
    from backend.app.admin.service.agent.tools import knowledge
    from backend.app.admin.service.agent.tools import file_ops
    from backend.app.admin.service.agent.tools import reasoning
    from backend.app.admin.service.agent.tools import web
    from backend.app.admin.service.agent.tools import data_tools
    from backend.app.admin.service.agent.tools import skills as skills_exec

    # tool_name → execute function 映射
    execute_map = {
        # 思考与规划
        "thinking": reasoning.execute_thinking,
        "todo_write": reasoning.execute_todo_write,
        # 网络工具
        "web_search": web.execute_web_search,
        "web_fetch": web.execute_web_fetch,
        # 数据分析
        "data_schema": data_tools.execute_data_schema,
        "data_analysis": data_tools.execute_data_analysis,
        # Skills 系统
        "read_skill": skills_exec.execute_read_skill,
        "execute_skill_script": skills_exec.execute_execute_skill_script,
        # 知识检索
        "semantic_search": knowledge.execute_semantic_search,
        "keyword_search": knowledge.execute_keyword_search,
        "get_chunks": knowledge.execute_get_chunks,
        "get_doc_info": knowledge.execute_get_doc_info,
        # 文件操作
        "search_docs": file_ops.execute_search_docs,
        "create_doc_dir": file_ops.execute_create_doc_dir,
        "move_docs_to_dir": file_ops.execute_move_docs_to_dir,
        "create_text_doc": file_ops.execute_create_text_doc,
        "create_spreadsheet": file_ops.execute_create_spreadsheet,
        "list_dirs": file_ops.execute_list_dirs,
        "get_doc_content": file_ops.execute_get_doc_content,
        "find_unclassified_docs": file_ops.execute_find_unclassified_docs,
        "tag_doc": file_ops.execute_tag_doc,
        "create_ppt": file_ops.execute_create_ppt,
    }

    registry = ToolRegistry()
    for tool_def_data in ALL_TOOL_DEFS:
        name = tool_def_data["name"]
        execute_fn = execute_map.get(name)
        if execute_fn is None:
            log.warning(f"[create_default_registry] 工具 '{name}' 无对应执行函数，跳过")
            continue

        tool = ToolDef(
            name=name,
            description=tool_def_data["description"],
            parameters=tool_def_data["parameters"],
            execute=execute_fn,
            required_caps=tool_def_data.get("caps", set()),
        )
        registry.register(tool)

    log.info(f"[create_default_registry] 注册了 {len(registry._tools)} 个工具")
    return registry
