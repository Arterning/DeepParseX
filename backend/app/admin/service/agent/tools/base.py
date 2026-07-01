from dataclasses import dataclass, field
from typing import Callable, Awaitable, Optional


@dataclass
class ToolDef:
    """工具定义——对应 WeKnora 的 types.Tool 接口"""

    name: str
    description: str
    parameters: dict  # JSON Schema dict（OpenAI function-calling 格式）
    execute: Callable[..., Awaitable[dict]]  # 异步执行函数
    # 所需知识库能力，"vector" / "keyword" / "graph"，空集 = 无依赖
    required_caps: set = field(default_factory=set)

    def to_openai_tool(self) -> dict:
        """转为 OpenAI function-calling 格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
