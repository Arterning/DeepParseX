#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import json
import re
from typing import Optional, Dict

from backend.common.log import log
from backend.app.admin.service.config_service import config_service
from backend.app.admin.service.llm import LLMFactory

# 有可选标签时：优先从列表中选择，也可生成新标签
_CLASSIFY_SYSTEM_PROMPT = (
    "你是一个文本分类助手。根据用户提供的文本内容，优先从给定的标签列表中选出所有匹配的标签；"
    "若现有标签无法准确描述文本内容，可额外补充 1~3 个新标签，新标签应简洁（2~8 个字）且与现有标签风格一致。"
    "只返回一个 JSON 数组，数组元素为标签名称字符串，不要包含任何解释或多余文字。"
    "如果没有任何匹配或值得新增的标签，返回空数组 []。"
)

# 无可选标签时：由 AI 自由生成
_GENERATE_SYSTEM_PROMPT = (
    "你是一个文档标签助手。根据用户提供的文本内容，为其生成 3~5 个简洁的中文标签。"
    "标签应准确描述文档的主题、领域或内容类型，每个标签 2~8 个字，避免过于宽泛。"
    "只返回一个 JSON 数组，数组元素为标签名称字符串，不要包含任何解释或多余文字。"
)


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def extract_json_from_text(text):
    """
    Extract JSON array from text that might contain additional content.

    Args:
        text: Text that may contain JSON

    Returns:
        The parsed JSON if found, None otherwise
    """
    # First, check if the text is wrapped in code blocks with triple backticks
    code_block_pattern = r'```(?:json)?\s*([\s\S]*?)```'
    code_match = re.search(code_block_pattern, text)
    if code_match:
        text = code_match.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start_idx = text.find('[')
        if start_idx == -1:
            return None

        bracket_count = 0
        complete_json = False
        for i in range(start_idx, len(text)):
            if text[i] == '[':
                bracket_count += 1
            elif text[i] == ']':
                bracket_count -= 1
                if bracket_count == 0:
                    json_str = text[start_idx:i + 1]
                    complete_json = True
                    break

        if complete_json:
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                fixed_json = re.sub(r'(\s*)(\w+)(\s*):(\s*)', r'\1"\2"\3:\4', json_str)
                fixed_json = re.sub(r',(\s*[\]}])', r'\1', fixed_json)
                try:
                    return json.loads(fixed_json)
                except json.JSONDecodeError:
                    pass
        else:
            objects = []
            obj_start = -1
            brace_count = 0
            for i in range(start_idx + 1, len(text)):
                if text[i] == '{':
                    if brace_count == 0:
                        obj_start = i
                    brace_count += 1
                elif text[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        obj_end = i
                        objects.append(text[obj_start:obj_end + 1])

            if objects:
                reconstructed_json = "[\n" + ",\n".join(objects) + "\n]"
                try:
                    return json.loads(reconstructed_json)
                except json.JSONDecodeError:
                    fixed_json = re.sub(r'(\s*)(\w+)(\s*):(\s*)', r'\1"\2"\3:\4', reconstructed_json)
                    fixed_json = re.sub(r',(\s*[\]}])', r'\1', fixed_json)
                    try:
                        return json.loads(fixed_json)
                    except json.JSONDecodeError:
                        pass

        return None


# ---------------------------------------------------------------------------
# Agent 工具调用接口（委托给 agent 模块）
# ---------------------------------------------------------------------------

# 兼容旧代码：CHAT_TOOLS 改为从 agent 模块动态获取
CHAT_TOOLS = []  # 延迟初始化，通过 _get_chat_tools() 获取


def _get_chat_tools() -> list[dict]:
    """获取当前所有已注册工具的 OpenAI function-calling 格式定义"""
    global CHAT_TOOLS
    if not CHAT_TOOLS:
        from backend.app.admin.service.agent import create_default_registry
        registry = create_default_registry()
        CHAT_TOOLS = registry.get_definitions()
    return CHAT_TOOLS


async def chat_with_tools(
    messages: list,
    system_prompt: Optional[str] = None,
    config: Optional[Dict] = None,
    max_tool_rounds: int = 10
) -> str:
    """
    带工具调用的对话接口。

    委托给 agent.AgentEngine 执行 ReAct 循环：
    LLM 返回 tool_calls → 执行工具 → 将结果追加到消息 → 再次调用 LLM，
    直到 LLM 返回普通文本或达到 max_tool_rounds 上限。

    Args:
        messages: 对话消息列表，格式同 OpenAI messages（role/content）
        system_prompt: 系统提示词
        config: 可选配置，支持 {"llm": {"temperature": 0.2}}
        max_tool_rounds: 最大工具调用轮次，防止无限循环

    Returns:
        LLM 最终的文本回复
    """
    from backend.app.admin.service.agent import run_agent
    return await run_agent(
        messages=messages,
        system_prompt=system_prompt,
        config=config,
        max_tool_rounds=max_tool_rounds,
    )


# ---------------------------------------------------------------------------
# 统一 LLM 调用接口
# ---------------------------------------------------------------------------

async def call_llm(user_prompt: str, system_prompt: Optional[str] = None,
                   config: Optional[Dict] = None) -> str:
    """
    统一的 LLM 调用接口（异步版本）

    Args:
        user_prompt: 用户提示词
        system_prompt: 系统提示词
        config: 配置对象，包含 provider 和其他设置

    Returns:
        模型响应字符串
    """
    merged_settings = await config_service.get_merged_settings()
    provider = merged_settings.LLM_PROVIDER if merged_settings.LLM_PROVIDER else 'openai'

    adapter_kwargs = {
        'api_key': merged_settings.LLM_API_KEY,
        'base_url': merged_settings.LLM_API_URL,
        'model': merged_settings.LLM_MODEL
    }

    adapter = LLMFactory.create_adapter(provider, **adapter_kwargs)

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, adapter.call, user_prompt, system_prompt, config)


# ---------------------------------------------------------------------------
# 业务方法
# ---------------------------------------------------------------------------

async def classify_text_tags(text: str, max_length: int = 2000) -> list[str]:
    """
    使用 LLM 对文本进行标签分类。

    - 数据库中有标签时：从现有标签中选择匹配的
    - 数据库中无标签时：由 AI 自由生成 3~5 个标签

    :param text: 输入文本
    :param max_length: 文本截取的最大长度
    :return: 标签名称列表
    """
    if not text or len(text.strip()) < 10:
        return []

    text_sample = text[:max_length] if len(text) > max_length else text

    from backend.app.admin.crud.crud_tag import tag_dao
    from backend.database.db_pg import async_db_session

    existing_names: list[str] = []
    try:
        async with async_db_session() as db:
            all_tags = await tag_dao.get_all(db)
            existing_names = [t.name for t in all_tags if t.name]
    except Exception as e:
        log.warning(f"[classify_text_tags] 获取标签列表失败: {repr(e)}")

    if existing_names:
        tag_list_str = "、".join(existing_names)
        user_prompt = (
            f"现有标签：{tag_list_str}\n\n"
            f"文本内容：\n{text_sample}\n\n"
            f"请从现有标签中选出所有与文本相关的标签，若现有标签不足以描述文本内容，可额外补充新标签。"
            f"以 JSON 数组格式返回所有标签名称。"
        )
        system_prompt = _CLASSIFY_SYSTEM_PROMPT
    else:
        user_prompt = (
            f"文本内容：\n{text_sample}\n\n"
            f"请为以上文本生成 3~5 个简洁的标签，以 JSON 数组格式返回。"
        )
        system_prompt = _GENERATE_SYSTEM_PROMPT

    try:
        response = await call_llm(user_prompt, system_prompt=system_prompt)

        start = response.find("[")
        end = response.rfind("]")
        if start == -1 or end == -1:
            log.warning(f"[classify_text_tags] LLM 返回内容无法解析为列表: {response!r}")
            return []

        raw_tags: list = json.loads(response[start: end + 1])
        valid_tags = [t.strip() for t in raw_tags if isinstance(t, str) and t.strip()]

        if valid_tags:
            log.info(f"[classify_text_tags] AI 标签结果: {valid_tags}")

        return valid_tags

    except Exception as e:
        log.error(f"[classify_text_tags] AI 标签分类失败: {repr(e)}")
        return []


class AiService:
    call_llm = staticmethod(call_llm)
    chat_with_tools = staticmethod(chat_with_tools)
    classify_text_tags = staticmethod(classify_text_tags)
    extract_json_from_text = staticmethod(extract_json_from_text)
    get_chat_tools = staticmethod(_get_chat_tools)


ai_service = AiService()
