"""
请求 / 响应 Pydantic 模型。
"""

from pydantic import BaseModel, Field


class ParseResponse(BaseModel):
    """OCR 解析结果。"""
    content: str = Field(description="文档完整内容（Markdown）")
    pages_content: list[str] = Field(description="分页内容数组，每页一个字符串")


class HealthResponse(BaseModel):
    status: str = "ok"
    backend: str
    max_file_mb: int
