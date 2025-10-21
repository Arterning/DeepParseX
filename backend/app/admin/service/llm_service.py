#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import requests
from openai import OpenAI
import time
from backend.common.log import log
from backend.core.conf import settings
from backend.app.admin.service.knowledge_graph.llm import call_llm

class LLMService:

    @staticmethod
    async def get_llm_response(system_context: str, user_input: str):
        
        # 创建配置对象
        config = {
            "provider": settings.LLM_PROVIDER,
            "llm": {
                "temperature": 0.7
            }
        }
        
        for attempt in range(1, 3):
            try:
                loop = asyncio.get_running_loop()
                # 调用call_llm方法
                reply = await loop.run_in_executor(None, call_llm, user_input, system_context, config)
                return reply
            except Exception as e:
                print(f"Attempt {attempt} failed: {e}")
                if attempt < 3:
                    time.sleep(0.5)  # 等待一段时间后重试
                else:
                    print("All attempts failed, returning None.")
                    return ""
                

llm_service = LLMService()