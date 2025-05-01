import os
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables from .env file
load_dotenv()


# Using a simple class for now, can switch to pydantic-settings later if needed
class Settings(BaseModel):
    embedding_model_name: str = "intfloat/multilingual-e5-small"  # Default
    api_token: Optional[str] = Field(
        default=None, description="Optional API token for authentication"
    )


@lru_cache  # Cache the settings object
def get_settings() -> Settings:
    """Loads settings, prioritizing environment variables."""
    model_name_from_env = os.getenv("EMBEDDING_MODEL_NAME")
    api_token_from_env = os.getenv("API_TOKEN")
    return Settings(
        embedding_model_name=(
            model_name_from_env
            if model_name_from_env
            else "intfloat/multilingual-e5-small"
        ),
        api_token=api_token_from_env,
    )


settings = get_settings()  # Load settings once on module import
