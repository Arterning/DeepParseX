from typing import List

from pydantic import BaseModel


# ── /embed ────────────────────────────────────────────────────────────────────

class EmbedRequest(BaseModel):
    texts: List[str]
    normalize: bool = True


class EmbedResponse(BaseModel):
    embeddings: List[List[float]]
    model: str
    dimension: int


# ── /v1/embeddings (Dify 兼容) ───────────────────────────────────────────────

class DifyEmbedRequest(BaseModel):
    model: str
    input: List[str]


class DifyEmbeddingData(BaseModel):
    object: str = "embedding"
    embedding: List[float]
    index: int


class DifyUsage(BaseModel):
    prompt_tokens: int = 0
    total_tokens: int = 0


class DifyEmbedResponse(BaseModel):
    object: str = "list"
    data: List[DifyEmbeddingData]
    model: str
    usage: DifyUsage = DifyUsage()


# ── /v1/rerank (Dify 兼容) ───────────────────────────────────────────────────

class DifyRerankRequest(BaseModel):
    model: str
    query: str
    documents: List[str]
    top_n: int | None = None


class DifyRerankDocument(BaseModel):
    text: str


class DifyRerankResult(BaseModel):
    index: int
    document: DifyRerankDocument
    relevance_score: float


class DifyRerankResponse(BaseModel):
    model: str
    results: List[DifyRerankResult]


# ── /chunk-embed ──────────────────────────────────────────────────────────────

class ChunkItem(BaseModel):
    text: str
    char_count: int
    embedding: List[float]


class ChunkEmbedRequest(BaseModel):
    text: str
    max_chars: int = 500
    normalize: bool = True


class ChunkEmbedResponse(BaseModel):
    chunks: List[ChunkItem]
    total_chunks: int
    model: str
    dimension: int