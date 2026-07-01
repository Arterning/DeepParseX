"""
MCP stdio 客户端

通过 subprocess 连接 MCP 服务器，使用 JSON-RPC 2.0 over stdin/stdout 通信。

协议（新行分隔的 JSON）：
1. 发送 initialize        → 握手
2. 发送 initialized       → 通知就绪
3. 发送 tools/list        → 发现工具
4. 发送 tools/call        → 调用工具
"""
import asyncio
import json
import subprocess
import time
from typing import Any, Optional

from backend.common.log import log


# 连接超时（秒）
CONNECT_TIMEOUT = 30
# 工具调用超时（秒）
CALL_TIMEOUT = 120


class MCPError(Exception):
    """MCP 协议错误"""
    pass


class MCPClient:
    """
    MCP stdio 客户端。

    用法:
        client = MCPClient("playwright", ["docker", "run", "-i", "--rm", ...])
        await client.connect()
        tools = await client.list_tools()
        result = await client.call_tool("browser_navigate", {"url": "https://..."})
        client.disconnect()
    """

    def __init__(self, name: str, command: str, args: list[str]):
        self.name = name
        self.command = command
        self.args = args
        self._proc: Optional[subprocess.Popen] = None
        self._request_id: int = 0
        self._server_info: dict = {}

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    async def connect(self) -> None:
        """启动子进程并完成 MCP 握手"""
        log.info(f"[MCP:{self.name}] 启动: {self.command} {' '.join(self.args[:4])}...")

        try:
            self._proc = subprocess.Popen(
                [self.command] + self.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
        except Exception as e:
            raise MCPError(f"启动进程失败: {e}")

        # 1. initialize
        result = await self._request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "lda-mcp-client", "version": "1.0"},
            },
            timeout=CONNECT_TIMEOUT,
        )
        self._server_info = result

        # 2. send initialized notification
        await self._notify("notifications/initialized", {})

        log.info(f"[MCP:{self.name}] 已连接, 服务器: {self._server_info.get('serverInfo', {}).get('name', 'unknown')}")

    async def list_tools(self) -> list[dict]:
        """发现 MCP 服务器提供的工具列表"""
        result = await self._request("tools/list", {}, timeout=CONNECT_TIMEOUT)
        tools = result.get("tools", [])
        log.info(f"[MCP:{self.name}] 发现 {len(tools)} 个工具: {[t.get('name') for t in tools]}")
        return tools

    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """
        调用 MCP 工具。

        Returns:
            {"content": [...], "isError": bool}
        """
        return await self._request(
            "tools/call",
            {"name": tool_name, "arguments": arguments},
            timeout=CALL_TIMEOUT,
        )

    async def _request(self, method: str, params: dict, timeout: int) -> dict:
        """发送 JSON-RPC 请求，等待响应"""
        req_id = self._next_id()
        payload = json.dumps({
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params,
        }, ensure_ascii=False)

        if self._proc is None or self._proc.stdin is None:
            raise MCPError("未连接")

        try:
            # 写
            self._proc.stdin.write(payload + "\n")
            self._proc.stdin.flush()

            # 读（超时保护）
            loop = asyncio.get_running_loop()
            response_raw = await asyncio.wait_for(
                loop.run_in_executor(None, self._proc.stdout.readline),
                timeout=timeout,
            )

            if not response_raw:
                raise MCPError("服务器已断开连接")

            response = json.loads(response_raw)

            if "error" in response:
                err = response["error"]
                raise MCPError(f"JSON-RPC error [{err.get('code')}]: {err.get('message', 'unknown')}")

            return response.get("result", {})

        except asyncio.TimeoutError:
            raise MCPError(f"{method} 超时 ({timeout}s)")

    async def _notify(self, method: str, params: dict) -> None:
        """发送 JSON-RPC 通知（无 id，无响应）"""
        payload = json.dumps({
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }, ensure_ascii=False)

        if self._proc and self._proc.stdin:
            self._proc.stdin.write(payload + "\n")
            self._proc.stdin.flush()

    def disconnect(self) -> None:
        """断开连接，终止子进程"""
        if self._proc:
            try:
                self._proc.stdin.close()
                self._proc.stdout.close()
                if self._proc.stderr:
                    self._proc.stderr.close()
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
            except Exception:
                pass
            self._proc = None
            log.info(f"[MCP:{self.name}] 已断开")


class MCPHttpClient:
    """
    MCP HTTP 客户端（备选方案，用于独立 playwright service）。

    通过 HTTP POST + JSON-RPC 2.0 与 MCP 服务器通信，无需子进程管理。

    用法:
        client = MCPHttpClient("playwright", "http://fba_playwright:3000/mcp")
        await client.connect()
        tools = await client.list_tools()
        result = await client.call_tool("browser_navigate", {"url": "https://..."})
    """

    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url.rstrip("/")
        self._request_id: int = 0
        self._session_id: str = ""  # MCP Session ID（initialize 响应头返回）

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    async def connect(self) -> None:
        """初始化连接（HTTP 模式下只需验证端点可达）"""
        import requests as sync_requests

        try:
            loop = asyncio.get_running_loop()
            resp = await loop.run_in_executor(
                None,
                lambda: sync_requests.post(
                    self.url,
                    json={
                        "jsonrpc": "2.0",
                        "id": self._next_id(),
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {},
                            "clientInfo": {"name": "lda-mcp-client", "version": "1.0"},
                        },
                    },
                    headers={
                        "Accept": "application/json, text/event-stream",
                        "Content-Type": "application/json",
                    },
                    timeout=CONNECT_TIMEOUT,
                ),
            )
            if resp.status_code != 200:
                raise MCPError(f"HTTP {resp.status_code}")

            # 捕获 MCP Session ID
            self._session_id = resp.headers.get("Mcp-Session-Id", "")
            log.debug(f"[MCP:{self.name}] Session ID: {self._session_id[:20] if self._session_id else '(无)'}")

            result = self._parse_sse_response(resp.text).get("result", {})
            log.info(f"[MCP:{self.name}] HTTP 已连接, 服务器: {result.get('serverInfo', {}).get('name', 'unknown')}")

            # 发送 initialized 通知
            notif_headers = {
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
            }
            if self._session_id:
                notif_headers["Mcp-Session-Id"] = self._session_id

            notif_resp = await loop.run_in_executor(
                None,
                lambda: sync_requests.post(
                    self.url,
                    json={
                        "jsonrpc": "2.0",
                        "method": "notifications/initialized",
                        "params": {},
                    },
                    headers=notif_headers,
                    timeout=5,
                ),
            )
            log.debug(f"[MCP:{self.name}] initialized 响应: HTTP {notif_resp.status_code} {notif_resp.text[:200]}")
        except Exception as e:
            raise MCPError(f"HTTP 连接失败: {e}")

    async def list_tools(self) -> list[dict]:
        """发现 MCP 工具"""
        result = await self._request("tools/list", {}, timeout=CONNECT_TIMEOUT)
        tools = result.get("tools", [])
        log.info(f"[MCP:{self.name}] tools/list 原始响应 keys: {list(result.keys())}")
        log.info(f"[MCP:{self.name}] 发现 {len(tools)} 个工具: {[t.get('name') for t in tools]}")
        return tools

    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """调用 MCP 工具"""
        return await self._request(
            "tools/call",
            {"name": tool_name, "arguments": arguments},
            timeout=CALL_TIMEOUT,
        )

    @staticmethod
    def _parse_sse_response(text: str) -> dict:
        """解析 SSE 格式的 MCP 响应。

        SSE 格式：
            event: message
            data: {"result":...}

        或纯 JSON 格式：
            {"result":...}
        """
        text = text.strip()
        # 如果是纯 JSON，直接解析
        if text.startswith("{"):
            return json.loads(text)

        # SSE 格式：逐行找 "data: " 开头的那一行
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("data: "):
                return json.loads(line[6:])
            if line.startswith("data:"):
                return json.loads(line[5:])

        return {}

    async def _request(self, method: str, params: dict, timeout: int) -> dict:
        """发送 JSON-RPC HTTP POST 请求"""
        import requests as sync_requests

        loop = asyncio.get_running_loop()
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id

        resp = await loop.run_in_executor(
            None,
            lambda: sync_requests.post(
                self.url,
                json={
                    "jsonrpc": "2.0",
                    "id": self._next_id(),
                    "method": method,
                    "params": params,
                },
                headers=headers,
                timeout=timeout,
            ),
        )

        log.debug(f"[MCP:{self.name}] {method} 响应: HTTP {resp.status_code} {resp.text[:300]}")
        if resp.status_code not in (200, 202):
            raise MCPError(f"HTTP {resp.status_code}: {resp.text[:200]}")

        data = self._parse_sse_response(resp.text)
        if "error" in data:
            err = data["error"]
            raise MCPError(f"JSON-RPC error [{err.get('code')}]: {err.get('message', 'unknown')}")

        return data.get("result", {})

    def disconnect(self) -> None:
        """HTTP 客户端无需断开（无状态）"""
        pass
