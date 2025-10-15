import numpy as np
import requests
from backend.core.conf import settings
from backend.common.log import log

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

# EMBEDDING
def request_text_to_vector(text, max_length=512):
    import json
    
    # 调用 LLM-Gateway 的 Embeddings API
    GATEWAY_API_KEY = settings.EMBEDDING_API_KEY
    MODEL_NAME = settings.EMBEDDING_MODEL
    API_ENDPOINT = settings.EMBEDDING_URL
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GATEWAY_API_KEY}"
    }
    
    data = {
        "model": MODEL_NAME,
        "input": text
    }
    
    try:
        response = requests.post(API_ENDPOINT, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        response_data = response.json()
        
        # 提取向量并保持原有返回格式
        embedding = response_data["data"][0]["embedding"]
        
        return [
            {
                "text": text,
                "embs": embedding
            }
        ]
    except Exception as e:
        log.error(f"Error in request_text_to_vector: {str(e)}")
        return []
        

# OCR
def process_file(file_name: str, file_data: bytes):
    """
    向服务端发送文件路径，获取处理后的 OCR 结果。
    
    :param file_path: 文件的完整路径，需为图片文件。
    :return: 服务端返回的处理结果，JSON 格式。
    """
    url = settings.OCR_URL
    try:
        data = {"task" : "默认算法"}
        mime_type =  'application/octet-stream'
        files = {'file': (file_name, file_data, mime_type) } 
        response = requests.post(url, data=data, files=files)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"请求失败，状态码：{response.status_code}")
            print(f"错误信息：{response.text}")
            return {
                "content": response.text
            }
    except Exception as e:
        log.error(f"[process_file]中出现错误：{str(e)}")
        return str(e)
        # raise e

        
# 分隔字符串
def split_string_by_length(input_string: str, chunk_size: int = 500) -> list[str]:
    """
    将输入字符串按照指定长度切分为多个子字符串。

    :param input_string: 要切分的输入字符串
    :param chunk_size: 每个子字符串的最大长度，默认为 500
    :return: 一个包含切分后的子字符串的列表
    """
    # 使用列表推导式切分字符串
    if not input_string:
        return []
    return [input_string[i:i + chunk_size] for i in range(0, len(input_string), chunk_size)]


def v1_embedding(text, max_length=512):
    url = settings.EMBEDDING_URL
    texts = split_string_by_length(text, chunk_size=max_length)
    payload = {
        "texts": texts,
    }
    # 发送 POST 请求
    try:
        response = requests.post(url, json=payload)
        # print("response", response)
        if response.status_code == 200:
            res = response.json()
            embeddings = res["embeddings"]
            result = []
            for i in range(len(embeddings)):
                result.append({
                    "embs": embeddings[i],
                    "text": texts[i]
                })
            return result
        else:
            log.error(f"Request failed with status code {response.status_code}")
            raise Exception(f"Request failed with status code {response.status_code}")
    except Exception as e:
        log.error(f"Error occurred: {str(e)}")
        raise e 
    

def v2_embedding(text, max_length=512):
    url = settings.EMBEDDING_URL
    
    # 准备请求体
    payload = {
        "text": text,
        "max_length":max_length
    }

    # 发送 POST 请求
    try:
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            return response.json()
        else:
            log.error(f"Request failed with status code {response.status_code}")
            return []
    except Exception as e:
        log.error(f"Error occurred: {str(e)}")
        return []



