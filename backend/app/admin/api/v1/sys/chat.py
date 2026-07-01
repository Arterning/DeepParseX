#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import json
from typing import Annotated

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from backend.app.admin.schema.chat import ChatParam, IdParam, TranslateParam, ChatDocParam
from backend.common.response.response_schema import ResponseModel, response_base
from backend.app.admin.service.chat_service import chat_service
from backend.app.admin.service.agent import AgentEngine, run_agent_stream, build_agent_system_prompt
from backend.app.admin.service.agent.skills import SkillsManager
from backend.app.admin.service.agent.tools import skills as skills_exec
from backend.app.admin.service.agent.mcp import MCPManager
from backend.app.admin.service.agent.tool_registry import create_default_registry, ToolRegistry
from backend.database.db_pg import async_db_session
from backend.app.admin.model.sys_chat_message import ChatMessage
from backend.common.log import log
from sqlalchemy import select
from pathlib import Path

router = APIRouter()

# ── 启动时初始化 ──

_skills_root = Path(__file__).resolve().parent.parent.parent.parent.parent.parent / "skills"
_skills_manager = SkillsManager(str(_skills_root))
_skills_manager.initialize()
skills_exec.set_skills_manager(_skills_manager)

# MCP 管理器（延迟连接）
_project_root = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
_mcp_config_path = str(_project_root / ".mcp.json")
_mcp_manager = MCPManager(_mcp_config_path)
_mcp_connected = False
_mcp_lock = asyncio.Lock()
_mcp_tools_count = 0


async def _ensure_mcp_connected():
    """确保 MCP 已连接（幂等，首次调用时连接）"""
    global _mcp_connected, _mcp_tools_count
    if _mcp_connected:
        return
    async with _mcp_lock:
        if _mcp_connected:
            return
        try:
            tools = await _mcp_manager.connect_all()
            _mcp_tools_count = len(tools)
            _mcp_connected = True
        except Exception as e:
            log.error(f"[chat] MCP 连接失败: {repr(e)}")


@router.post('/stream', summary='Agent 流式对话（SSE）')
async def chat_stream(obj: ChatParam) -> StreamingResponse:
    """
    Agent 模式 SSE 流式对话接口。

    事件类型：
    - status:  会话状态（start / done / error / max_rounds）
    - tool_call: 工具调用（name, args, round）
    - thought: 思考步骤（thinking 工具）
    - tool_result: 工具执行结果摘要
    - answer: 最终回答
    """
    # 1. 加载历史消息
    messages = []
    if obj.session_id and obj.send_history is not False:
        async with async_db_session() as db:
            result = await db.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id == obj.session_id)
                .order_by(ChatMessage.created_time.asc())
            )
            for msg in result.scalars().all():
                role = "user" if msg.sender == "user" else "assistant"
                messages.append({"role": role, "content": msg.content})

    messages.append({"role": "user", "content": obj.question})
    log.debug(f"[chat_stream] session={obj.session_id} history={len(messages)-1}")

    # 2. 构建 system prompt（含 skills 元数据 Level 1）
    skills_metadata = _skills_manager.get_all_metadata() if _skills_manager.is_enabled else None
    system_prompt = build_agent_system_prompt(skills_metadata=skills_metadata)

    # 3. 确保 MCP 连接（首次调用时懒加载）
    await _ensure_mcp_connected()

    # 4. 返回 SSE 流
    async def event_generator():
        # 构建带 MCP 工具的 registry
        engine = AgentEngine()
        if _mcp_connected:
            for mcp_tool in _mcp_manager.get_all_tools():
                engine.registry.register_mcp_tool(mcp_tool)

        async for sse_event in engine.run_stream(
            messages=messages,
            system_prompt=system_prompt,
        ):
            yield sse_event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
        },
    )


@router.post('', summary='对话')
async def chat(obj: ChatParam, request: Request) -> ResponseModel:
    """
    RAG 对话接口

    返回数据格式:
    {
        "answer": "回答内容，使用 [1]、[2] 标注引用来源",
        "references": [
            {
                "ref_index": 1,
                "doc_id": 123,
                "doc_name": "文档名称",
                "content_preview": "引用内容摘要"
            }
        ]
    }
    """
    data = await chat_service.rag_chat(obj=obj)
    return response_base.success(data=data)
    
    


@router.post('_doc', summary='文档片段对话')
async def chat_doc(obj: ChatDocParam, request: Request) -> ResponseModel:
    data = await chat_service.chat_doc(
        question=obj.question,
        context=obj.context,
        doc_id=obj.doc_id
    )
    return response_base.success(data=data)
