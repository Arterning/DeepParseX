#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调用 embedding-api 进行文本向量化。

配置说明：
  EMBEDDING_URL 复用为 embedding-api 的 base URL，例如：
    EMBEDDING_URL='http://localhost:8003'
"""
import numpy as np
import aiohttp

from backend.common.log import log
from backend.app.admin.service.config_service import config_service


def _random_vector(text: str, dim: int = 1024) -> dict:
    """出错时返回随机向量作为备份，与 text_processor.py 保持一致。"""
    return {
        "text": text,
        "embs": np.random.rand(dim).tolist(),
    }


async def embed_text_chunks(text: str, max_length: int = 1000) -> list[dict]:
    """
    调用 embedding-api /chunk-embed 接口，对文本分块并向量化。

    :param text: 输入文本
    :param max_length: 每个分块的最大字符数
    :return: [{"text": str, "embs": List[float]}, ...]
    """
    merged_settings = await config_service.get_merged_settings()
    base_url = (merged_settings.EMBEDDING_URL or "").rstrip("/")
    url = f"{base_url}/chunk-embed"

    payload = {
        "text": text,
        "max_chars": max_length,
        "normalize": True,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    log.error(f"[embed_text_chunks] embedding-api 返回异常 {resp.status}: {error_text}")
                    return [_random_vector(text)]

                data = await resp.json()

        return [
            {"text": chunk["text"], "embs": chunk["embedding"]}
            for chunk in data["chunks"]
        ]

    except Exception as e:
        log.error(f"[embed_text_chunks] 调用 embedding-api 失败: {repr(e)}")
        return [_random_vector(text)]


async def embed_texts(texts: list[str]) -> list[dict]:
    """
    调用 embedding-api /embed 接口，对已分好的文本列表批量向量化。

    :param texts: 文本列表
    :return: [{"text": str, "embs": List[float]}, ...]
    """
    if not texts:
        return []

    merged_settings = await config_service.get_merged_settings()
    base_url = (merged_settings.EMBEDDING_URL or "").rstrip("/")
    url = f"{base_url}/embed"

    payload = {
        "texts": texts,
        "normalize": True,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    log.error(f"[embed_texts] embedding-api 返回异常 {resp.status}: {error_text}")
                    return [_random_vector(t) for t in texts]

                data = await resp.json()

        embeddings = data["embeddings"]
        return [
            {"text": t, "embs": embeddings[i]}
            for i, t in enumerate(texts)
        ]

    except Exception as e:
        log.error(f"[embed_texts] 调用 embedding-api 失败: {repr(e)}")
        return [_random_vector(t) for t in texts]


class EmbeddingService:
    embed_text_chunks = staticmethod(embed_text_chunks)
    embed_texts = staticmethod(embed_texts)


embedding_service = EmbeddingService()
