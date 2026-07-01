from backend.app.admin.service.llm.base import LLMAdapter
from backend.app.admin.service.llm.openai_adapter import OpenAIAdapter
from backend.app.admin.service.llm.claude_adapter import ClaudeAdapter
from backend.app.admin.service.llm.gemini_adapter import GeminiAdapter


class LLMFactory:
    """LLM 工厂类"""

    @staticmethod
    def create_adapter(provider: str, **kwargs) -> LLMAdapter:
        """
        根据提供商创建适配器

        Args:
            provider: 提供商名称 (openai, claude, gemini, etc.)
            **kwargs: 各提供商所需的参数
        """
        if provider.lower() in ['openai', 'zhipu', 'deepseek', 'moonshot', 'yi', 'ollama']:
            return OpenAIAdapter(
                api_key=kwargs['api_key'],
                base_url=kwargs['base_url'],
                model=kwargs['model']
            )
        elif provider.lower() == 'claude':
            return ClaudeAdapter(
                api_key=kwargs['api_key'],
                model=kwargs.get('model', 'claude-3-5-sonnet-20241022')
            )
        elif provider.lower() == 'gemini':
            return GeminiAdapter(
                api_key=kwargs['api_key'],
                model=kwargs.get('model', 'gemini-pro')
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")
