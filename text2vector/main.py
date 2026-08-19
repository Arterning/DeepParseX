import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from sentence_transformers import CrossEncoder, SentenceTransformer

from chunker import chunk_text
from schema import (
    ChunkEmbedRequest,
    ChunkEmbedResponse,
    ChunkItem,
    DifyEmbedRequest,
    DifyEmbedResponse,
    DifyEmbeddingData,
    DifyRerankDocument,
    DifyRerankRequest,
    DifyRerankResponse,
    DifyRerankResult,
    EmbedRequest,
    EmbedResponse,
)

load_dotenv()

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
RERANK_MODEL = os.getenv("RERANK_MODEL")

model: SentenceTransformer = None
rerank_model: CrossEncoder = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, rerank_model
    if EMBEDDING_MODEL:
        print(f"Loading embedding model: {EMBEDDING_MODEL}")
        model = SentenceTransformer(EMBEDDING_MODEL)
        print(f"Embedding dimension: {model.get_sentence_embedding_dimension()}")
    if RERANK_MODEL:
        print(f"Loading rerank model: {RERANK_MODEL}")
        rerank_model = CrossEncoder(RERANK_MODEL)
    yield
    model = None
    rerank_model = None


app = FastAPI(title="Embedding API", lifespan=lifespan)


@app.post("/embed", response_model=EmbedResponse)
def embed(request: EmbedRequest):
    if not request.texts:
        raise HTTPException(status_code=400, detail="texts must not be empty")
    if model is None:
        raise HTTPException(status_code=503, detail="embedding model not loaded")
    vectors = model.encode(
        request.texts,
        normalize_embeddings=request.normalize,
        show_progress_bar=False,
    )
    return EmbedResponse(
        embeddings=vectors.tolist(),
        model=EMBEDDING_MODEL,
        dimension=model.get_sentence_embedding_dimension(),
    )


@app.post("/v1/embeddings", response_model=DifyEmbedResponse)
def dify_embed(request: DifyEmbedRequest):
    if not request.input:
        raise HTTPException(status_code=400, detail="input must not be empty")
    if model is None:
        raise HTTPException(status_code=503, detail="embedding model not loaded")
    vectors = model.encode(
        request.input,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    data = [
        DifyEmbeddingData(embedding=v.tolist(), index=i)
        for i, v in enumerate(vectors)
    ]
    return DifyEmbedResponse(data=data, model=request.model)


@app.post("/v1/rerank", response_model=DifyRerankResponse)
def dify_rerank(request: DifyRerankRequest):
    if not request.query:
        raise HTTPException(status_code=400, detail="query must not be empty")
    if not request.documents:
        raise HTTPException(status_code=400, detail="documents must not be empty")
    if rerank_model is None:
        raise HTTPException(status_code=503, detail="rerank model not loaded")

    pairs = [(request.query, doc) for doc in request.documents]
    scores = rerank_model.predict(pairs, show_progress_bar=False)

    indexed = list(enumerate(scores.tolist()))
    indexed.sort(key=lambda x: x[1], reverse=True)

    top_n = request.top_n or len(indexed)
    results = [
        DifyRerankResult(
            index=orig_idx,
            document=DifyRerankDocument(text=request.documents[orig_idx]),
            relevance_score=float(score),
        )
        for orig_idx, score in indexed[:top_n]
    ]

    return DifyRerankResponse(model=request.model, results=results)


@app.post("/chunk-embed", response_model=ChunkEmbedResponse)
def chunk_and_embed(request: ChunkEmbedRequest):
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="text must not be empty")
    if request.max_chars < 10:
        raise HTTPException(status_code=400, detail="max_chars must be >= 10")
    if model is None:
        raise HTTPException(status_code=503, detail="embedding model not loaded")

    chunks = chunk_text(request.text, max_chars=request.max_chars)
    if not chunks:
        raise HTTPException(status_code=400, detail="No chunks generated")

    vectors = model.encode(
        chunks,
        normalize_embeddings=request.normalize,
        show_progress_bar=False,
    )

    return ChunkEmbedResponse(
        chunks=[
            ChunkItem(text=c, char_count=len(c), embedding=v.tolist())
            for c, v in zip(chunks, vectors)
        ],
        total_chunks=len(chunks),
        model=EMBEDDING_MODEL,
        dimension=model.get_sentence_embedding_dimension(),
    )


@app.get("/health")
def health():
    return {
        "status": "ok",
        "embedding_model": EMBEDDING_MODEL,
        "rerank_model": RERANK_MODEL,
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8003"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
