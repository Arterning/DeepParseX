from abc import ABC, abstractmethod
from typing import Optional, Dict


class LLMAdapter(ABC):
    """LLM 适配器基类"""

    @abstractmethod
    def call(self, user_prompt: str, system_prompt: Optional[str] = None,
             config: Optional[Dict] = None) -> str:
        pass
