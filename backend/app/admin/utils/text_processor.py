import numpy as np
import requests
from backend.core.conf import settings
from backend.common.log import log
from backend.app.admin.service.config_service import config_service
from backend.app.admin.utils.config_manager import get_merged_settings
from backend.app.admin.utils.text_splitter import (
    split_string_by_length,
    is_markdown,
    split_text_by_paragraphs,
    split_markdown_by_structure,
    split_long_block,
    smart_split_text
)


def random_vector(text, dim=1024):
    # 出错时返回随机向量作为备份
    import numpy as np
    np_vector = np.random.rand(dim)
    list_vector = np_vector.tolist()
    
    return [
        {
            "text": text,
            "embs": list_vector
        }
    ]

async def embed_text_chunks(text, max_length=1000):
    # 直接调用异步版本的get_merged_settings
    merged_settings = await get_merged_settings()
    MODEL_NAME = merged_settings.EMBEDDING_MODEL
    if MODEL_NAME == "text-embedding-3-small":
        return await text_embedding(text, max_length=max_length)
    else:
        return await legacy_embedding(text, max_length=max_length)

async def text_embedding(text, max_length=1000):
    import json
    import aiohttp
    # 使用文件中已定义的全局smart_split_text函数
    texts = smart_split_text(text, max_chunk_size=max_length)

    # 直接调用异步版本的get_merged_settings
    merged_settings = await get_merged_settings()
    
    # 调用 LLM-Gateway 的 Embeddings API
    GATEWAY_API_KEY = merged_settings.EMBEDDING_API_KEY
    MODEL_NAME = merged_settings.EMBEDDING_MODEL
    API_ENDPOINT = merged_settings.EMBEDDING_URL
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GATEWAY_API_KEY}"
    }

    embeddings = []

    async with aiohttp.ClientSession() as session:
        for text in texts:
            data = {
                "model": MODEL_NAME,
                "input": text
            }
        
            try:
                async with session.post(API_ENDPOINT, headers=headers, json=data, timeout=60) as response:
                    response.raise_for_status()
                    response_data = await response.json()
                    
                    if 'data' in response_data and isinstance(response_data['data'], list):
                        for item in response_data['data']:
                            if 'embedding' in item:
                                embeddings.append({
                                    "text": text,
                                    "embs": item['embedding']
                                })
            except Exception as e:
                log.error(f"[text_embedding] API调用失败: {str(e)}")
                # 出错时返回随机向量
                embeddings.extend(random_vector(text))
        
    return embeddings

# OCR
async def process_file(file_name: str, file_data: bytes):
    """
    向服务端发送文件路径，获取处理后的 OCR 结果。
    
    :param file_path: 文件的完整路径，需为图片文件。
    :return: 服务端返回的处理结果，JSON 格式。
    """
    # 直接调用异步版本的get_merged_settings
    merged_settings = await get_merged_settings()
    url = merged_settings.OCR_URL
    try:
        # 使用aiohttp替代requests进行异步HTTP请求
        import aiohttp
        import aiohttp.multipart
        
        data = {"task" : "默认算法"}
        mime_type = 'application/octet-stream'
        
        # 准备多部分表单数据
        form_data = aiohttp.FormData()
        form_data.add_field('file', file_data, filename=file_name, content_type=mime_type)
        for key, value in data.items():
            form_data.add_field(key, value)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=form_data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    print(f"请求失败，状态码：{response.status}")
                    print(f"错误信息：{error_text}")
                    return {
                        "content": error_text
                    }
    except Exception as e:
        log.error(f"[process_file]中出现错误：{str(e)}")
        return str(e)

        
# 分隔字符串 - 已移至text_splitter.py


async def v1_embedding(text, max_length=1000):
    import aiohttp
    # 直接调用异步版本的get_merged_settings
    merged_settings = await get_merged_settings()
    url = merged_settings.EMBEDDING_URL
    
    headers = {
        "Content-Type": "application/json"
    }
    
    # 将文本分割成小块
    texts = split_string_by_length(text, max_length)
    
    embeddings = []
    
    async with aiohttp.ClientSession() as session:
        for chunk in texts:
            data = {
                "text": chunk
            }
            
            try:
                async with session.post(url, headers=headers, json=data, timeout=60) as response:
                    response.raise_for_status()
                    
                    result = await response.json()
                    if "data" in result:
                        embeddings.append({
                            "text": chunk,
                            "embs": result["data"]
                        })
            except Exception as e:
                log.error(f"[v1_embedding] API调用失败: {str(e)}")
                embeddings.extend(random_vector(chunk))
    
    return embeddings 
    

async def legacy_embedding(text, max_length=1000):
    import aiohttp
    # 直接调用异步版本的get_merged_settings
    merged_settings = await get_merged_settings()
    url = merged_settings.EMBEDDING_URL
    
    try:
        headers = {
            "Content-Type": "application/json"
        }
        
        data = {
            "text": text
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data, timeout=60) as response:
                response.raise_for_status()
                
                result = await response.json()
                if "data" in result:
                    return [
                        {
                            "text": text,
                            "embs": result["data"]
                        }
                    ]
    except Exception as e:
        log.error(f"[legacy_embedding] API调用失败: {str(e)}")
        return random_vector(text)



