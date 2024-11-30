import requests
import time

from pathlib import Path

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



def get_qw_response(content, max_retries=3, delay=0.5):
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                'http://172.17.0.1:8130/v1/chat/completions',
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
            
if __name__ =="__main__":
    question_prompt = "请分析下面的文本包含的账号密码，并直接返回结果:\n"
    content   = """
网站/应用名称	用户名/邮箱	密码	安全问题及答案	注册邮箱	注册日期	最后登录日期	账户类型	备注
Example.com	user123	skdjf89hghjH						
AnotherSite.net	email@example	asdjf90sdcjH						
BankApp	user456	skdjf91hghjH						
SocialMedia	user789	skdjf92hghjH						
OnlineShop	buyer123	skdjf93hghjH						
CloudStorage	clouduser	skdjf94hghjH						
EmailProvider	emailuser	skdjf95hghjH						

"""
    input_llm = question_prompt + content
    res = get_qw_response(input_llm)
    print("-"*10)
    print('模型回复:')
    print(res)