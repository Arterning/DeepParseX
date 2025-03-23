
from typing import Annotated,List,Dict
import json

import numpy as np 
import faiss
import time
import requests

from loguru import logger

def get_llm_response(content, max_retries=3, delay=0.5):
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                'http://127.0.0.1:8103/v1/chat/completions',
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
            

def request_text_to_vector(text , max_length):
    url = "http://0.0.0.0:8104/text_to_vector"
    
    # 准备请求体
    payload = {"text": text,
               "max_length":max_length}

    # 发送 POST 请求
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        return response.json()['json_data']
    else:
        raise Exception(f"Request failed with status code {response.status_code}")

def search_rag_inthedocker(text:str , 
               database_jsondata: List[Dict],
               max_length = 512,
               check_topk = 5
               ):
    """
    四个参数分别是：
    text : 用户提问
    database_jsondata : 所有文本向量。为list，包含dict
    
    
    """

    question_text = text
    max_length = int(max_length)
    check_topk = int(check_topk)
    
    # 将 解码
    database =  json.loads(database_jsondata)

    # 将反序列化的列表转换回 numpy 数组
    for i in range(len(database)):
        i_data = database[i]
        database[i]["embs"] = np.array(i_data["embs"])
    
    # 假设database已经存储了N个文本片段的向量，为list【dict】
    time1 = time.perf_counter()


    # 一、提问向量化
    question_text_emb = request_text_to_vector(text=question_text,max_length=max_length) # -> [1,1024]
    question_text_emb = json.loads(question_text_emb)   
    question_text_emb = np.array(question_text_emb[0]["embs"])
    # 在开头增加一个维度
    question_text_emb  = question_text_emb[np.newaxis, :]


    

    # 二、 数据库文本、向量整合，用于查询。

    all_texts = np.array([ x["text"]  for x in database])

    all_embs = [ np.array(x["embs"]) for x in database]

    all_embs = np.stack(all_embs,axis=0)# [N,1024]
    logger.info(f"rag:数据库向量shape:{all_embs.shape}")
    
    ## 三、faiss 查询对象创建

    index_object = faiss.IndexFlatL2(1024)  # 创建一个 L2 距离的索引对象
    index_object.add(all_embs)

    time2 = time.perf_counter()

    # 四、执行查询，返回 K 个最近邻和其距离
    distances, indices = index_object.search(question_text_emb , check_topk)

    time3 = time.perf_counter()

    context_indexes = indices[0]

    context = all_texts[context_indexes]

    # logger.info(f"{context}")

    # 整理上下文:

    context = "\n".join(context)

    logger.info(f"查询到的文本:\n{context }")

    # 大模型问答：
    template = (
        "上下文信息如下。\n"
        "---\n"
        f"{context}\n"
        "---\n"
        "请根据上下文信息而不是先验知识来回答以下的查询。"
        "作为一个人工智能助手，你的回答要尽可能严谨。"
        f"提问:{question_text}"
        "回答："
    )

    respn = get_llm_response(content=template ) 
    time4 = time.perf_counter()

    logger.info(f"faiss查询对象创建用时:{time2-time1:.4f}s")
    logger.info(f"faiss查询向量,topk={check_topk},用时:{time3-time2:.4f}s")
    logger.info(f"rag大模型问答用时:{time4-time3:.4f}s")
    return respn








if __name__ =="__main__":

    # 测试在容器内部直接进行向量计算

    ## 初始化数据库 内数据：

    database_jsondata = json.dumps([
        {"text":"唐源黄宁唐源黄宁唐源黄宁唐源黄宁唐源黄宁唐源黄宁唐源黄宁唐源黄宁唐源黄宁",
         "embs":[0.2]  * 1024},
         {"text":"专利文档专利文档专利文档专利文档专利文档专利文档专利文档专利文档",
         "embs":[0.2]  * 1024},

    ] , ensure_ascii=False)


    question_text  = "啊啊啊啊啊啊啊啊"


    searched_context = search_rag_inthedocker(text = question_text, 
               database_jsondata = database_jsondata , 
               max_length = 512,
               check_topk = 5
               )
    print("----")
    print(searched_context)



    pass