from pydantic import BaseModel, Field


class EmbeddingRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, description="List of texts to embed")


class EmbeddingResponse(BaseModel):
    embeddings: list[list[float]] = Field(
        ..., description="List of computed embeddings"
    )
    model_name: str = Field(..., description="Name of the model used")
