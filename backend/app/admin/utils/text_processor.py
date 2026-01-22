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

# 全局标签向量缓存
_tag_embeddings_cache = {}

# 预设标签列表（标签名称 -> 描述性关键词，用于计算向量）
PRESET_TAGS = {
    "政治": "政治 政府 政策 选举 国务院 人大 党委 领导 官员 治理 执政 施政",
    "军事": "军事 国防 武器 军队 战争 导弹 航母 坦克 士兵 作战 演习 军演",
    "经济": "经济 宏观经济 产业 贸易 GDP 就业 市场 企业 商业 工业 制造业",
    "科技": "科技 技术 创新 互联网 人工智能 芯片 半导体 软件 硬件 研发 专利",
    "财经": "财经 金融 投资 股票 银行 基金 证券 理财 资本 融资 上市 债券",
    "历史": "历史 历史事件 古代 文物 考古 朝代 遗址 历史人物 传统 文献",
    "文化": "文化 艺术 文学 传统文化 非遗 戏曲 书法 绘画 音乐 舞蹈 民俗",
    "教育": "教育 学校 高考 大学 培训 学术 教学 学生 老师 课程 考试 招生",
    "医疗健康": "医疗 健康 医院 疾病 药品 公共卫生 医生 治疗 手术 疫苗 康复",
    "社会民生": "社会 民生 社会保障 住房 养老 社区 福利 扶贫 公益 慈善",
    "法律": "法律 法规 司法 诉讼 合同 刑事 民事 法院 律师 判决 立法 执法",
    "能源环保": "能源 环保 气候变化 新能源 太阳能 风能 碳排放 污染 绿色 可持续",
    "外交": "外交 国际关系 大使馆 峰会 条约 双边 多边 出访 会谈 国际组织",
    "农业": "农业 农村 种植 畜牧 粮食 农民 农产品 耕地 收成 灌溉 养殖",
    "交通": "交通 铁路 航空 物流 高速公路 地铁 公交 运输 港口 机场 高铁",
    "体育": "体育 运动 比赛 奥运会 足球 篮球 运动员 冠军 联赛 训练 竞技",
    "娱乐": "娱乐 影视 音乐 游戏 明星 电影 电视剧 综艺 演出 直播 网红",
}


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


async def get_tag_embeddings(model_name: str = None, model_path: str = None) -> dict:
    """
    获取预设标签的嵌入向量（带缓存）

    :param model_name: 模型名称
    :param model_path: 本地模型路径
    :return: {标签名称: 向量} 字典
    """
    global _tag_embeddings_cache

    # 从配置读取模型信息
    if not model_name:
        merged_settings = await config_service.get_merged_settings()
        model_name = merged_settings.EMBEDDING_MODEL or "BAAI/bge-large-zh-v1.5"
        model_path = getattr(merged_settings, 'EMBEDDING_MODEL_PATH', None) or None

    cache_key = model_path if model_path else model_name

    if cache_key not in _tag_embeddings_cache:
        log.info(f"正在计算预设标签的嵌入向量...")
        model = get_embedding_model(model_name, model_path)

        tag_names = list(PRESET_TAGS.keys())
        tag_descriptions = list(PRESET_TAGS.values())

        # 批量计算标签描述的嵌入向量
        vectors = model.encode(tag_descriptions, normalize_embeddings=True)

        _tag_embeddings_cache[cache_key] = {
            tag_names[i]: vectors[i] for i in range(len(tag_names))
        }
        log.info(f"预设标签嵌入向量计算完成，共 {len(tag_names)} 个标签")

    return _tag_embeddings_cache[cache_key]


async def classify_text_tags(text: str, threshold: float = 0.5, max_length: int = 2000) -> list[str]:
    """
    根据文本内容自动分类，返回匹配的标签列表

    :param text: 输入文本
    :param threshold: 相似度阈值，超过此值的标签才会被返回
    :param max_length: 文本截取的最大长度（避免过长文本影响性能）
    :return: 匹配的标签名称列表
    """
    if not text or len(text.strip()) < 10:
        return []

    # 截取文本前 max_length 个字符用于分类
    text_sample = text[:max_length] if len(text) > max_length else text

    try:
        # 从配置读取模型信息
        merged_settings = await config_service.get_merged_settings()
        model_name = merged_settings.EMBEDDING_MODEL or "BAAI/bge-large-zh-v1.5"
        model_path = getattr(merged_settings, 'EMBEDDING_MODEL_PATH', None) or None

        # 获取模型和标签向量
        model = get_embedding_model(model_name, model_path)
        tag_embeddings = await get_tag_embeddings(model_name, model_path)

        # 计算文本的嵌入向量
        text_vector = model.encode([text_sample], normalize_embeddings=True)[0]

        # 计算文本与各标签的余弦相似度
        matched_tags = []
        for tag_name, tag_vector in tag_embeddings.items():
            # 由于向量已经归一化，直接点积即为余弦相似度
            similarity = np.dot(text_vector, tag_vector)
            if similarity >= threshold:
                matched_tags.append((tag_name, float(similarity)))

        # 按相似度降序排序
        matched_tags.sort(key=lambda x: x[1], reverse=True)

        # 只返回标签名称
        result = [tag for tag, _ in matched_tags]

        if result:
            log.info(f"文本自动分类结果: {result}")

        return result

    except Exception as e:
        log.error(f"[classify_text_tags] 标签分类失败: {str(e)}")
        return []
