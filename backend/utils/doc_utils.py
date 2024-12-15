import requests
import time
import numpy as np
import json
from pathlib import Path
import faiss
from typing import Annotated,List,Dict

## 1 PDF 请求
def post_pdf_recog(input_path,
                   output_folder,
                   
                   language):
    url = "http://172.17.0.1:8101/process_imgpdf_files/"
    data = {
        "input_path": input_path,   # 替换为实际的输入文件路径
        "output_folder": output_folder,  # 替换为实际的输出文件路径
        "language" : language
    }
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            return response.json()
        else:
            print("post_pdf_recog failed:", response.status_code, response.text)
    except Exception as e:
        print(f"request error {e}")


## 2  text 请求
def post_text_recog(input_path,
                   output_folder,
                   language):
    url = "http://172.17.0.1:8101/process_text_files/"
    data = {
        "input_path": input_path,   # 替换为实际的输入文件路径
        "output_folder": output_folder,  # 替换为实际的输出文件路径
        "language" : language
    }
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            return response.json()
        else:
            print("post_text_recog failed:", response.status_code, response.text)
    except Exception as e:
        print(f"request error {e}")


## 3 image 请求
def post_imagesocr_recog(input_path,
                   output_folder,
                   language):
    url = "http://172.17.0.1:8101/process_imgocr_files/"
    data = {
        "input_path": input_path,   # 替换为实际的输入文件路径
        "output_folder": output_folder,  # 替换为实际的输出文件路径
        "language" : language
    }
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            return response.json()
        else:
            print("post_imagesocr_recog failed:", response.status_code, response.text)
    except Exception as e:
        print(f"request error {e}")



## 4 audios 请求
def post_audios_recog(input_path,
                   output_folder,
                   language):
    url = "http://172.17.0.1:8101/process_audio_files/"
    data = {
        "input_path": input_path,   # 替换为实际的输入文件路径
        "output_folder": output_folder,  # 替换为实际的输出文件路径
        "language" : language
    }
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            return response.json()
        else:
            print("post_audios_recog failed:", response.status_code, response.text)
    except Exception as e:
        print(f"request error {e}")


## 5 emails 处理 
def post_emails_recog(input_path, # 输入含有邮件的目录
                   output_folder, # 附录下载目录
                   output_folder2, # 附录二次识别输出目录
                   language,
                   language2):
    url = "http://172.17.0.1:8101/process_email_files/"
    data = {
        "input_path": input_path,  
        "output_folder": output_folder, 
        "output_folder2": output_folder2,
        "language" : language,
        "language2" : language2
    }
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            return response.json()
        else:
            print("post_emails_recog failed:", response.status_code, response.text)
    except Exception as e:
        print(f"request error {e}")

# 所有文件类型
def request_process_allkinds_filepath(file_path: str):
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
        print(f"请求过程中出现错误：{e}")
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
        return response.json()['json_data']
    else:
        raise Exception(f"Request failed with status code {response.status_code}")
    
def request_rag_01(text, database,max_length=512,check_topk=5):
    url = "http://127.0.0.1:8104/search_rag"
    max_length = str(max_length)
    check_topk = str(check_topk)

    headers = {
        'accept': 'application/json',
    }

    data = {
        'text': text,
        "database_jsondata":database,
        "max_length":str(max_length),
        "check_topk":check_topk
    }
    import time
    st = time.time()
    print(f"给大模型发请求    {st}")
    response = requests.post(url, headers=headers, data=data)
    st1 = time.time()
    print(f"接受到大模型响应     {st1}")
    print(f"大模型总时间{st1-st}")
    if response.status_code != 200:
        print(f"Response Status Code: {response.status_code}")
        print(f"Response Text: {response.text}")  # 错误信息
        try:
            print(f"Response JSON: {response.json()}")
        except ValueError:
            pass
        raise Exception(f"Request failed with status code {response.status_code}")
    
    return response.json()['response']

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
    # logger.info(f"rag:数据库向量shape:{all_embs.shape}")
    
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

    # logger.info(f"查询到的文本:\n{context }")

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

    # logger.info(f"faiss查询对象创建用时:{time2-time1:.4f}s")
    # logger.info(f"faiss查询向量,topk={check_topk},用时:{time3-time2:.4f}s")
    # logger.info(f"rag大模型问答用时:{time4-time3:.4f}s")
    return respn



# 获取账号密码
def get_accountPassw(content_list)->list:
    url = "http://172.17.0.1:8105/get_ipAdress_or_AccountPasswd"
    res_list = []
    for content in content_list:
        try:
            # 将文件路径作为表单数据发送
            # input_type = "ipAdress" input_type = "AccountPasswd"
            
            data = {"input_content": content,"input_type":"AccountPasswd"}
            
            # 发送 POST 请求
            response = requests.post(url, data=data)
            
            # 检查响应状态
            if response.status_code == 200:
                
                res_list.append(response.json()['response']) 
            else:
                print(f"请求失败，状态码：{response.status_code}")
                print(f"错误信息：{response.text}")
                return None
        except Exception as e:
            print(f"请求过程中出现错误：{e}")
            return None
    return res_list


def get_ipaddr(conent_list)->list:
    url = "http://172.17.0.1:8105/get_ipAdress_or_AccountPasswd"
    res_list = []
    for content in conent_list:
        try:
            # 将文件路径作为表单数据发送
            # input_type = "ipAdress" input_type = "AccountPasswd"
            
            data = {"input_content": content,"input_type":"ipAdress"}
            
            # 发送 POST 请求
            response = requests.post(url, data=data)
            
            # 检查响应状态
            if response.status_code == 200:
                temp =  json.loads(response.json()['response'])
                if temp:
                    res_list.extend(temp)  
            else:
                print(f"请求失败，状态码：{response.status_code}")
                print(f"错误信息：{response.text}")
                return None
        except Exception as e:
            print(f"请求过程中出现错误：{e}")
            return None
    return res_list


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