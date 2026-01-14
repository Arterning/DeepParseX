import numpy as np
from backend.core.conf import settings
from backend.common.log import log
from backend.app.admin.service.config_service import config_service
from backend.app.admin.utils.text_splitter import (
    split_string_by_length,
    is_markdown,
    split_text_by_paragraphs,
    split_markdown_by_structure,
    split_long_block,
    smart_split_text
)

# 全局嵌入模型缓存（支持多个模型）
_embedding_models = {}


def get_embedding_model(model_name: str, model_path: str = None):
    """
    获取嵌入模型（按模型标识缓存）

    :param model_name: 模型名称（用于从网络下载，如 BAAI/bge-large-zh-v1.5）
    :param model_path: 本地模型路径，优先使用；为空时从网络下载
    :return: SentenceTransformer 模型实例
    """
    global _embedding_models

    # 使用本地路径或模型名称作为缓存 key
    cache_key = model_path if model_path else model_name

    if cache_key not in _embedding_models:
        from sentence_transformers import SentenceTransformer

        # 优先使用本地路径
        load_path = model_path if model_path else model_name
        log.info(f"正在加载嵌入模型: {load_path}")
        _embedding_models[cache_key] = SentenceTransformer(load_path)
        log.info(f"嵌入模型加载完成: {load_path}")

    return _embedding_models[cache_key]


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
    """
    使用本地嵌入模型计算文本向量

    :param text: 输入文本
    :param max_length: 文本分块的最大长度
    :return: 包含文本和嵌入向量的列表
    """
    # 从配置读取模型名称和本地路径
    merged_settings = await config_service.get_merged_settings()
    model_name = merged_settings.EMBEDDING_MODEL or "BAAI/bge-large-zh-v1.5"
    model_path = getattr(merged_settings, 'EMBEDDING_MODEL_PATH', None) or None

    # 使用智能分割函数将文本分块
    texts = smart_split_text(text, max_chunk_size=max_length)

    embeddings = []

    try:
        model = get_embedding_model(model_name, model_path)

        # 批量计算嵌入向量
        vectors = model.encode(texts, normalize_embeddings=True)

        for i, chunk in enumerate(texts):
            embeddings.append({
                "text": chunk,
                "embs": vectors[i].tolist()
            })
    except Exception as e:
        log.error(f"[embed_text_chunks] 本地嵌入模型调用失败: {str(e)}")
        # 出错时返回随机向量
        for chunk in texts:
            embeddings.extend(random_vector(chunk))

    return embeddings


# OCR
async def process_file(file_name: str, file_data: bytes):
    """
    向服务端发送文件路径，获取处理后的 OCR 结果。
    
    :param file_path: 文件的完整路径，需为图片文件。
    :return: 服务端返回的处理结果，JSON 格式。
    """
    merged_settings = await config_service.get_merged_settings()
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
