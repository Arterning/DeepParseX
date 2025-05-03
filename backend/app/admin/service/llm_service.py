#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from openai import OpenAI
import time
from backend.common.log import log
from backend.core.conf import settings

class LLMService:

    @staticmethod
    async def get_llm_response(system_context: str, user_input: str):
        llm_model =  settings.LLM_MODEL
        if "deepseek" in llm_model:
            # 使用 DeepSeek API
            response = await LLMService.get_deepseek_api_response(system_context, user_input)
            return response
        else:
            # 使用 VLLM API
            response = LLMService.get_api_response(system_context, user_input)
            return response


    @staticmethod
    async def get_deepseek_api_response(system_context: str, user_input: str):
        api_key = settings.LLM_API_KEY
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_context},
                {"role": "user", "content": user_input},
            ],
            stream=False
        )

        return response.choices[0].message.content
    



    @staticmethod
    def get_api_response(system_context: str, user_input: str):
        url = settings.LLM_API_URL
        model = settings.LLM_MODEL
        for attempt in range(1, 3):
            try:
                response = requests.post(
                    url,
                    json={
                        'model': model,
                        'max_tokens': 1000,
                        'temperature': 0.3,
                        "messages": [
                            {
                                "role": "system", 
                                "content": system_context
                            },
                            {
                                "role": "user",
                                "content": user_input,
                            }
                        ],
                    }
                )
                # 尝试获取响应，如果没有异常则返回内容
                reply = response.json()['choices'][0]['message']['content']
                return reply
            except Exception as e:
                print(f"Attempt {attempt} failed: {e}")
                if attempt < 3:
                    time.sleep(0.5)  # 等待一段时间后重试
                else:
                    print("All attempts failed, returning None.")
                    return None
                

llm_service = LLMService()