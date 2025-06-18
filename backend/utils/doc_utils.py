import requests
import time
from backend.core.conf import settings
from backend.common.log import log


# 所有文件类型
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
            return None
    except Exception as e:
        log.error(f"[process_file]中出现错误：{str(e)}")
        raise e

        
# 文本的摘要
def get_llm_abstract( content ):

    question = "请生成以下文本的简洁的摘要，突出核心内容。请你必须使用中文描述，不超过500字："
    template = f"{question}\n{content}"

    llm_respone = get_llm_response(content= template )
    return llm_respone



# excel请求
def get_llm_response( content, max_retries=3, delay=0.5):
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                'http://172.17.0.1:8103/v1/chat/completions',
                json={
                    'model': 'Qwen2.5-7B-Instruct',
                    "messages": [
                        {
                            "role": "user",
                            "content": content,
                        }
                    ],
                }
            )
            # 尝试获取响应，如果没有异常则返回内容
            reply = response.json()['choices'][0]['message']['content']
            return reply
        except Exception as e:
            print(f"Attempt {attempt} failed: {e}")
            if attempt < max_retries:
                time.sleep(delay)  # 等待一段时间后重试
            else:
                print("All attempts failed, returning None.")
                return None
    

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


def request_text_to_vector_bge(text, max_length=512):
    url = "http://192.168.200.229:8002/embeddings"
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
    
def request_text_to_vector(text, model="bge-large-zh-v1.5", max_length=512):
    if model == "bge-large-zh-v1.5":
        return request_text_to_vector_bge(text, max_length=max_length)
    else :
        return request_text_to_vector_api(text, max_length=max_length)
        

def request_text_to_vector_api(text, max_length=512):
    url = "http://172.17.0.1:8104/text_to_vector"
    
    # 准备请求体
    payload = {"text": text,
               "max_length":max_length}

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



