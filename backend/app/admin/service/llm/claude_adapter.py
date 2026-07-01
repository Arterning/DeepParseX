from typing import Optional, Dict
import requests

from backend.app.admin.service.llm.base import LLMAdapter


class ClaudeAdapter(LLMAdapter):
    """Claude (Anthropic) 适配器"""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.anthropic.com/v1/messages"

    def call(self, user_prompt: str, system_prompt: Optional[str] = None,
             config: Optional[Dict] = None) -> str:
        max_tokens = 1000
        temperature = 0.2

        if config:
            llm_config = config.get("llm", {})
            max_tokens = llm_config.get("max_tokens", max_tokens)
            temperature = llm_config.get("temperature", temperature)

        payload = {
            'model': self.model,
            'max_tokens': max_tokens,
            'temperature': temperature,
            'messages': [{"role": "user", "content": user_prompt}]
        }

        if system_prompt:
            payload['system'] = system_prompt

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }

        response = requests.post(self.base_url, headers=headers, json=payload)

        if response.status_code == 200:
            return response.json()['content'][0]['text']
        else:
            raise Exception(f"API request failed: {response.text}")
