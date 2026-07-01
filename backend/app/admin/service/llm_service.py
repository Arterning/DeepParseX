#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import requests
from openai import OpenAI
import time
from backend.common.log import log
from backend.core.conf import settings
from backend.app.admin.service.ai_service import call_llm

class LLMService:

    @staticmethod
    async def get_llm_response(system_context: str, user_input: str, temperature: float = 0.7):
        
        # 创建配置对象
        config = {
            "provider": settings.LLM_PROVIDER,
            "llm": {
                "temperature": temperature
            }
        }
        
        for attempt in range(1, 3):
            try:
                # 调用异步版本的call_llm方法
                reply = await call_llm(user_input, system_context, config)
                return reply
            except Exception as e:
                print(f"Attempt {attempt} failed: {e}")
                if attempt == 2:
                    print("All attempts failed, returning None.")
                    raise
                else:
                    await asyncio.sleep(0.5)  # 等待一段时间后重试
                       

llm_service = LLMService()