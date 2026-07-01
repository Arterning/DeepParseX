from typing import Optional, Dict
import requests

from backend.app.admin.service.llm.base import LLMAdapter


class GeminiAdapter(LLMAdapter):
    """Google Gemini 适配器"""

    def __init__(self, api_key: str, model: str = "gemini-pro"):
        self.api_key = api_key
        self.model = model
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def call(self, user_prompt: str, system_prompt: Optional[str] = None,
             config: Optional[Dict] = None) -> str:
        temperature = 0.2

        if config:
            llm_config = config.get("llm", {})
            temperature = llm_config.get("temperature", temperature)

        # Gemini 将 system prompt 合并到 user prompt
        full_prompt = user_prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{user_prompt}"

        payload = {
            "contents": [{
                "parts": [{"text": full_prompt}]
            }],
            "generationConfig": {
                "temperature": temperature
            }
        }

        response = requests.post(
            f"{self.base_url}?key={self.api_key}",
            headers={"Content-Type": "application/json"},
            json=payload
        )

        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            raise Exception(f"API request failed: {response.text}")
