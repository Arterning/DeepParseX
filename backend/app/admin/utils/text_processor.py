import numpy as np
import requests
from backend.core.conf import settings
from backend.common.log import log
from backend.app.admin.service.config_service import config_service
from backend.app.admin.utils.config_manager import get_merged_settings


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

        
# 分隔字符串
import re

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

def is_markdown(text: str) -> bool:
    """
    简单检测文本是否为Markdown格式
    
    :param text: 要检测的文本
    :return: 如果是Markdown格式返回True，否则返回False
    """
    # 常见的Markdown特征
    markdown_patterns = [
        r'^#{1,6}\s',  # 标题
        r'^\*\s|^-\s|^\+\s',  # 无序列表
        r'^\d+\.\s',  # 有序列表
        r'^>\s',  # 引用
        r'^```',  # 代码块开始
        r'`[^`]+`',  # 行内代码
        r'\*\*[^*]+\*\*|__[^_]+__',  # 粗体
        r'\*[^*]+\*|_[^_]+_',  # 斜体
        r'\!\[.*\]\(.*\)',  # 图片
        r'\[.*\]\(.*\)',  # 链接
    ]
    
    # 计算匹配的模式数量
    matches = 0
    lines = text.split('\n')[:20]  # 只检查前20行
    
    for line in lines:
        for pattern in markdown_patterns:
            if re.search(pattern, line):
                matches += 1
                break  # 每行只计算一次匹配
    
    # 如果匹配的模式数超过阈值，认为是Markdown
    return matches >= 3

def split_text_by_paragraphs(text: str) -> list[str]:
    """
    按照段落分割文本
    
    :param text: 要分割的文本
    :return: 段落列表
    """
    # 使用两个或更多换行符作为段落分隔符
    paragraphs = re.split(r'\n\s*\n', text)
    # 去除空段落和前后空白
    return [p.strip() for p in paragraphs if p.strip()]

def split_markdown_by_structure(markdown_text: str) -> list[str]:
    """
    按照Markdown结构分割文本
    
    :param markdown_text: 要分割的Markdown文本
    :return: 结构化的文本块列表
    """
    blocks = []
    current_block = []
    in_code_block = False
    code_block_start = None
    
    lines = markdown_text.split('\n')
    
    for line in lines:
        stripped_line = line.strip()
        
        # 检查代码块
        if stripped_line.startswith('```'):
            if in_code_block:
                # 代码块结束
                current_block.append(line)
                blocks.append('\n'.join(current_block))
                current_block = []
                in_code_block = False
                code_block_start = None
            else:
                # 代码块开始
                if current_block:  # 如果当前有积累的内容，先保存
                    blocks.append('\n'.join(current_block))
                    current_block = []
                current_block.append(line)
                in_code_block = True
                code_block_start = stripped_line
            continue
        
        # 在代码块内，直接添加
        if in_code_block:
            current_block.append(line)
            continue
        
        # 检查标题
        if stripped_line.startswith('#'):
            if current_block:  # 如果当前有积累的内容，先保存
                blocks.append('\n'.join(current_block))
                current_block = []
            current_block.append(line)
            blocks.append('\n'.join(current_block))
            current_block = []
            continue
        
        # 检查列表项
        if stripped_line.startswith(('* ', '- ', '+ ', '1. ', '2. ', '3. ', '4. ', '5. ', '6. ', '7. ', '8. ', '9. ')):
            # 如果当前块不是列表，先保存当前块
            if current_block and not current_block[-1].strip().startswith(('* ', '- ', '+ ', '1. ', '2. ', '3. ', '4. ', '5. ', '6. ', '7. ', '8. ', '9. ')):
                blocks.append('\n'.join(current_block))
                current_block = []
            current_block.append(line)
            continue
        
        # 检查引用
        if stripped_line.startswith('>'):
            # 如果当前块不是引用，先保存当前块
            if current_block and not current_block[-1].strip().startswith('>'):
                blocks.append('\n'.join(current_block))
                current_block = []
            current_block.append(line)
            continue
        
        # 普通文本行
        if stripped_line:  # 非空行
            current_block.append(line)
        else:  # 空行，可能是段落结束
            if current_block:
                blocks.append('\n'.join(current_block))
                current_block = []
    
    # 处理剩余内容
    if current_block:
        blocks.append('\n'.join(current_block))
    
    return blocks

def split_long_block(block: str, max_length: int = 500) -> list[str]:
    """
    将过长的文本块进一步分割，尽量在句子结束处分割
    
    :param block: 要分割的文本块
    :param max_length: 最大长度
    :return: 分割后的文本块列表
    """
    if len(block) <= max_length:
        return [block]
    
    # 尝试在句号、问号、感叹号后分割
    sentence_endings = re.split(r'(。|！|？|\.|\?|!)(\s|$)', block)
    chunks = []
    current_chunk = ''
    
    for i in range(0, len(sentence_endings), 3):
        sentence = sentence_endings[i]
        punctuation = sentence_endings[i+1] if i+1 < len(sentence_endings) else ''
        whitespace = sentence_endings[i+2] if i+2 < len(sentence_endings) else ''
        
        sentence_with_end = sentence + punctuation + whitespace
        
        if len(current_chunk) + len(sentence_with_end) <= max_length:
            current_chunk += sentence_with_end
        else:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = sentence_with_end
            else:
                # 如果单个句子就超过最大长度，强制按长度分割
                chunks.extend(split_string_by_length(sentence_with_end, max_length))
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

def smart_split_text(text: str, max_chunk_size: int = 500) -> list[str]:
    """
    智能分割文本，根据文本类型选择合适的分割策略
    
    :param text: 要分割的文本
    :param max_chunk_size: 每个块的最大长度
    :return: 分割后的文本块列表
    """
    if not text:
        return []
    
    # 检测是否为Markdown
    if is_markdown(text):
        # 按Markdown结构分割
        blocks = split_markdown_by_structure(text)
    else:
        # 按段落分割
        blocks = split_text_by_paragraphs(text)
    
    # 处理过长的块
    result = []
    for block in blocks:
        if len(block) > max_chunk_size:
            result.extend(split_long_block(block, max_chunk_size))
        else:
            result.append(block)
    
    return result


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



