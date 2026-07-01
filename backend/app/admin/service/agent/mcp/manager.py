"""
MCP Manager

读取 .mcp.json 配置，连接所有 MCP 服务器，将远程工具包装为 Agent 工具。
"""
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Callable, Awaitable

from backend.common.log import log
from backend.app.admin.service.agent.mcp.client import MCPClient, MCPHttpClient, MCPError


@dataclass
class MCPToolDef:
    """MCP 工具包装（兼容 ToolDef 的 name/description/parameters/execute 接口）"""
    name: str
    description: str
    parameters: dict
    execute: Callable[..., Awaitable[dict]]
    required_caps: set = field(default_factory=set)

    def to_openai_tool(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


def _convert_mcp_schema(mcp_schema: dict) -> dict:
    """将 MCP tool inputSchema 转为 OpenAI function-calling JSON Schema"""
    schema = dict(mcp_schema)
    # 确保顶层有 type
    if "type" not in schema:
        schema["type"] = "object"
    # 移除 MCP 特有字段
    schema.pop("additionalProperties", None)
    schema.pop("$schema", None)
    return schema


def _format_mcp_result(result: dict) -> str:
    """将 MCP tools/call 返回结果格式化为可读文本"""
    content = result.get("content", [])
    is_error = result.get("isError", False)

    parts = []
    for item in content:
        if item.get("type") == "text":
            parts.append(item.get("text", ""))
        elif item.get("type") == "image":
            mime = item.get("mimeType", "image/unknown")
            data_len = len(item.get("data", ""))
            parts.append(f"[图片: {mime}, {data_len} bytes]")
        elif item.get("type") == "resource":
            parts.append(f"[资源: {item.get('resource', {})}]")

    text = "\n".join(parts) if parts else "(无输出)"

    if is_error:
        text = f"[错误] {text}"

    return text


class MCPManager:
    """
    MCP 服务器管理器。

    使用方式:
        manager = MCPManager("/path/to/.mcp.json")
        await manager.connect_all()
        for tool in manager.get_all_tools():
            registry.register(tool)
    """

    def __init__(self, config_path: str):
        self._config_path = Path(config_path)
        self._clients: dict[str, MCPClient] = {}
        self._tools: list[MCPToolDef] = []

    def load_config(self) -> dict:
        """读取 .mcp.json 配置"""
        if not self._config_path.exists():
            log.info(f"[MCPManager] 配置文件不存在: {self._config_path}")
            return {}

        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            servers = config.get("mcpServers", {})
            log.info(f"[MCPManager] 加载 {len(servers)} 个 MCP 服务器配置")
            return servers
        except Exception as e:
            log.error(f"[MCPManager] 读取配置失败: {repr(e)}")
            return {}

    async def connect_all(self) -> list[MCPToolDef]:
        """连接所有 MCP 服务器并发现工具"""
        servers = self.load_config()
        self._tools.clear()

        for server_name, server_cfg in servers.items():
            # 跳过注释字段
            if server_name.startswith("_"):
                continue

            url = server_cfg.get("url", "")
            command = server_cfg.get("command", "")
            args = server_cfg.get("args", [])

            # HTTP 模式（优先）
            if url:
                client = MCPHttpClient(server_name, url)
            elif command:
                client = MCPClient(server_name, command, args)
            else:
                log.warning(f"[MCPManager] 服务器 {server_name} 缺少 url 或 command，跳过")
                continue

            try:
                await client.connect()
                mcp_tools = await client.list_tools()

                for mt in mcp_tools:
                    tool_name = mt.get("name", "")
                    if not tool_name:
                        continue

                    # 生成 Agent 工具名：mcp_{server}_{tool}
                    safe_server = server_name.replace("-", "_").replace(" ", "_")
                    safe_tool = tool_name.replace("-", "_").replace(" ", "_")
                    agent_name = f"mcp_{safe_server}_{safe_tool}"

                    # 包装为工具
                    mcp_schema = mt.get("inputSchema", {"type": "object", "properties": {}})

                    tool = MCPToolDef(
                        name=agent_name,
                        description=f"[MCP: {server_name}] {mt.get('description', tool_name)}",
                        parameters=_convert_mcp_schema(mcp_schema),
                        execute=self._make_execute(server_name, tool_name),
                    )
                    self._tools.append(tool)

                self._clients[server_name] = client

            except MCPError as e:
                log.error(f"[MCPManager] 连接 {server_name} 失败: {e}")
                client.disconnect()
            except Exception as e:
                log.error(f"[MCPManager] {server_name} 异常: {repr(e)}")
                client.disconnect()

        log.info(f"[MCPManager] 共发现 {len(self._tools)} 个 MCP 工具")
        return self._tools

    def _make_execute(self, server_name: str, tool_name: str):
        """创建 execute 闭包，捕获 server_name 和 tool_name"""
        async def execute(**kwargs) -> dict:
            client = self._clients.get(server_name)
            if not client:
                return {"error": f"MCP 服务器 {server_name} 未连接"}

            # 尝试调用，断线重试一次
            for attempt in range(2):
                try:
                    result = await client.call_tool(tool_name, kwargs)
                    output = _format_mcp_result(result)
                    return {
                        "success": not result.get("isError", False),
                        "output": output,
                        "server": server_name,
                        "tool": tool_name,
                    }
                except MCPError as e:
                    if attempt == 0:
                        log.warning(f"[MCP:{server_name}] 调用失败，尝试重连...")
                        try:
                            client.disconnect()
                            await client.connect()
                        except Exception:
                            pass
                    else:
                        return {"error": f"[MCP:{server_name}] {str(e)}"}

            return {"error": "未知错误"}

        return execute

    def get_all_tools(self) -> list[MCPToolDef]:
        return list(self._tools)

    def disconnect_all(self) -> None:
        """断开所有 MCP 服务器连接"""
        for client in self._clients.values():
            client.disconnect()
        self._clients.clear()
