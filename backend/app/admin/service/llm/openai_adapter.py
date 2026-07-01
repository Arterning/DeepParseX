from typing import Optional, Dict
import requests

from backend.app.admin.service.llm.base import LLMAdapter


class OpenAIAdapter(LLMAdapter):
    """OpenAI 及兼容格式的适配器（DeepSeek / 智谱 / Moonshot / Yi / Ollama 等）"""

    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    def call(self, user_prompt: str, system_prompt: Optional[str] = None,
             config: Optional[Dict] = None) -> str:
        max_tokens = 1000
        temperature = 0.2

        if config:
            llm_config = config.get("llm", {})
            max_tokens = llm_config.get("max_tokens", max_tokens)
            temperature = llm_config.get("temperature", temperature)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        payload = {
            'model': self.model,
            # 'max_tokens': max_tokens,
            'temperature': temperature,
            'messages': messages
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        response = requests.post(self.base_url, headers=headers, json=payload)

        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            raise Exception(f"API request failed: {response.text}")
