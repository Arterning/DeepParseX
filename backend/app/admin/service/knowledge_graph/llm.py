"""LLM interaction utilities for knowledge graph generation."""
import json
import re
import requests
import asyncio
from backend.core.conf import settings
from backend.app.admin.utils.config_manager import get_merged_settings
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import requests


def get_merged_settings_sync():
    """
    同步获取合并后的配置
    """
    try:
        return asyncio.run(get_merged_settings())
    except Exception as e:
        # 出错时返回原始settings作为备用
        print(f"Failed to get merged settings: {str(e)}")
        return settings

class LLMAdapter(ABC):
    """LLM适配器基类"""
    
    @abstractmethod
    def call(self, user_prompt: str, system_prompt: Optional[str] = None, 
             config: Optional[Dict] = None) -> str:
        pass

class OpenAIAdapter(LLMAdapter):
    """OpenAI及兼容格式的适配器"""
    
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

# 工厂类
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


# 统一调用接口
def call_llm(user_prompt: str, system_prompt: Optional[str] = None, 
             config: Optional[Dict] = None) -> str:
    """
    统一的 LLM 调用接口
    
    Args:
        user_prompt: 用户提示词
        system_prompt: 系统提示词
        config: 配置对象，包含 provider 和其他设置
    
    Returns:
        模型响应字符串
    """
    # 从config_manager获取合并后的配置（数据库配置优先于环境变量配置）
    merged_settings = get_merged_settings_sync()
    provider = merged_settings.LLM_PROVIDER if merged_settings.LLM_PROVIDER else 'openai'
    
    # 从配置中提取参数
    adapter_kwargs = {
        'api_key': merged_settings.LLM_API_KEY,
        'base_url': merged_settings.LLM_API_URL,
        'model': merged_settings.LLM_MODEL
    }
    
    if config and 'llm' in config:
        adapter_kwargs.update(config['llm'])
    
    adapter = LLMFactory.create_adapter(provider, **adapter_kwargs)
    return adapter.call(user_prompt, system_prompt, config)

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
        print("Found JSON in code block, extracting content...")
    
    try:
        # Try direct parsing in case the response is already clean JSON
        return json.loads(text)
    except json.JSONDecodeError:
        # Look for opening and closing brackets of a JSON array
        start_idx = text.find('[')
        if start_idx == -1:
            print("No JSON array start found in text")
            return None
            
        # Simple bracket counting to find matching closing bracket
        bracket_count = 0
        complete_json = False
        for i in range(start_idx, len(text)):
            if text[i] == '[':
                bracket_count += 1
            elif text[i] == ']':
                bracket_count -= 1
                if bracket_count == 0:
                    # Found the matching closing bracket
                    json_str = text[start_idx:i+1]
                    complete_json = True
                    break
        
        # Handle complete JSON array
        if complete_json:
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                print("Found JSON-like structure but couldn't parse it.")
                print("Trying to fix common formatting issues...")
                
                # Try to fix missing quotes around keys
                fixed_json = re.sub(r'(\s*)(\w+)(\s*):(\s*)', r'\1"\2"\3:\4', json_str)
                # Fix trailing commas
                fixed_json = re.sub(r',(\s*[\]}])', r'\1', fixed_json)
                
                try:
                    return json.loads(fixed_json)
                except:
                    print("Could not fix JSON format issues")
        else:
            # Handle incomplete JSON - try to complete it
            print("Found incomplete JSON array, attempting to complete it...")
            
            # Get all complete objects from the array
            objects = []
            obj_start = -1
            obj_end = -1
            brace_count = 0
            
            # First find all complete objects
            for i in range(start_idx + 1, len(text)):
                if text[i] == '{':
                    if brace_count == 0:
                        obj_start = i
                    brace_count += 1
                elif text[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        obj_end = i
                        objects.append(text[obj_start:obj_end+1])
            
            if objects:
                # Reconstruct a valid JSON array with complete objects
                reconstructed_json = "[\n" + ",\n".join(objects) + "\n]"
                try:
                    return json.loads(reconstructed_json)
                except json.JSONDecodeError:
                    print("Couldn't parse reconstructed JSON array.")
                    print("Trying to fix common formatting issues...")
                    
                    # Try to fix missing quotes around keys
                    fixed_json = re.sub(r'(\s*)(\w+)(\s*):(\s*)', r'\1"\2"\3:\4', reconstructed_json)
                    # Fix trailing commas
                    fixed_json = re.sub(r',(\s*[\]}])', r'\1', fixed_json)
                    
                    try:
                        return json.loads(fixed_json)
                    except:
                        print("Could not fix JSON format issues in reconstructed array")
            
        print("No complete JSON array could be extracted")
        return None