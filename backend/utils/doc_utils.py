import requests
import time
from backend.common.log import log


# 所有文件类型
def process_file(file_path: str):
    """
    向服务端发送文件路径，获取处理后的 OCR 结果。
    
    :param file_path: 文件的完整路径，需为图片文件。
    :return: 服务端返回的处理结果，JSON 格式。
    """
    url = "http://172.17.0.1:8105/process_allkinds_filepath"
    try:
        # 将文件路径作为表单数据发送
        data = {"filepath": file_path}
        
        # 发送 POST 请求
        response = requests.post(url, data=data)
        
        # 检查响应状态
        if response.status_code == 200:
            
            return response.json()
        else:
            print(f"请求失败，状态码：{response.status_code}")
            print(f"错误信息：{response.text}")
            return None
    except Exception as e:
        log.error(f"[process_file]中出现错误：{str(e)}")
        return None



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
            
# 3.6 向大模型请求文本的摘要。模板函数之一

def get_llm_abstract( content ):

    question = "请生成以下文本的简洁的摘要，突出核心内容。请你必须使用中文描述，不超过500字："
    template = f"{question}\n{content}"

    llm_respone = get_llm_response(content= template )
    return llm_respone




def request_text_to_vector(text , max_length=512):
    url = "http://172.17.0.1:8104/text_to_vector"
    
    # 准备请求体
    payload = {"text": text,
               "max_length":max_length}

    # 发送 POST 请求
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        return response.json()
    else:
        log.error(f"Request failed with status code {response.status_code}")
        return []



content_list = ["""故事：最后的胜利198.168.0.1 woshishen10
在遥远的未来，地球的多个
198.168.0.1
国家因资源枯竭和政治纷争

 爆发了全面战争。战火弥漫，整
198.168.0.1 198.168.0.1
个世界陷入了混乱与毁灭之中。各国政府为了争夺有限的资源，不择手段，甚至动用了最先进的战争技术。那些曾经在历史上被视为遥不可及的超级武器，现在已成为普通战士的日常装备。

在这场浩劫中，有一支特殊的 

部队，198.168.0.1 123456789  他们是由各国精英组成 146.5.8.9  !@#$%win10"""]
# print(get_ipaddr(content_list)[0])