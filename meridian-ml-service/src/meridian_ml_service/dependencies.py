from typing import Annotated, Union
import asyncio
from functools import lru_cache

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN

from .config import settings
from .embeddings import ModelComponents, load_embedding_model

# Global lock for model loading
_model_lock = asyncio.Lock()
_model_instance: Union[ModelComponents, None] = None


async def get_embedding_model() -> ModelComponents:
    """FastAPI dependency to get the loaded embedding model components in a thread-safe way."""
    global _model_instance

    if _model_instance is not None:
        return _model_instance

    async with _model_lock:
        # double-check pattern to avoid race conditions
        if _model_instance is not None:
            return _model_instance

        try:
            _model_instance = load_embedding_model()
            return _model_instance
        except Exception as e:
            # Consider how to handle model loading failure more gracefully in API
            # Maybe return HTTP 503 Service Unavailable?
            print(f"FATAL: Could not provide embedding model: {e}")
            raise  # Let FastAPI handle internal server error for now


ModelDep = Annotated[ModelComponents, Depends(get_embedding_model)]

api_key_header = APIKeyHeader(name="X-API-Token", auto_error=False)


async def verify_token(api_key: Union[str, None] = Security(api_key_header)) -> None:
    print(f"api_key: {api_key}")
    print(f"settings.api: {settings.api_token}")
    if settings.api_token is None:
        return  # auth is disabled if no token is configured

    if api_key != settings.api_token:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="Invalid or missing API token"
        )
