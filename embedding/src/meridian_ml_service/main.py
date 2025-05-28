import numpy as np
from fastapi import Depends, FastAPI, HTTPException

from .config import settings
from .dependencies import (
    ModelDep,
    verify_token,
    get_embedding_model,
)  # Import auth dependency
from .embeddings import compute_embeddings
from .schemas import EmbeddingRequest, EmbeddingResponse

app = FastAPI(
    title="Meridian ML Service",
    description="Handles ML tasks like embeddings and clustering.",
    version="0.1.0",
)


# Simple root endpoint for health check
@app.get("/")
async def read_root():
    return {"status": "ok", "service": "Meridian ML Service"}


@app.get("/ping")
async def ping():
    return {"pong": True}


@app.post("/embeddings", response_model=EmbeddingResponse)
async def api_compute_embeddings(
    request: EmbeddingRequest,
    model_components: ModelDep,  # ModelDep already includes Depends
    _: None = Depends(verify_token),
):
    """
    Computes embeddings for the provided list of texts.
    """
    print(f"Received request to embed {len(request.texts)} texts.")
    try:
        embeddings_np: np.ndarray = compute_embeddings(
            texts=request.texts,
            model_components=model_components,
        )

        embeddings_list: list[list[float]] = embeddings_np.tolist()

        return EmbeddingResponse(
            embeddings=embeddings_list, model_name=settings.embedding_model_name
        )
    except Exception as e:
        print(f"ERROR during embedding computation: {e}")
        # Consider more specific error handling based on exception types
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during embedding computation: {str(e)}",
        ) from e
