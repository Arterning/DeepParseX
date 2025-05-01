from functools import lru_cache
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F  # noqa: N812
from tqdm import tqdm
from transformers import AutoModel, AutoTokenizer

from .config import settings  # Import settings instance

# Re-using your type alias and functions, adding type hints and minor adjustments
ModelComponents = tuple[Any, Any, torch.device]


@lru_cache(maxsize=1)  # Cache the loaded model globally
def load_embedding_model() -> ModelComponents:
    """Loads tokenizer, model from HuggingFace based on settings."""
    model_name = settings.embedding_model_name
    print(f"Attempting to load embedding model: {model_name}")
    try:
        tokenizer = AutoTokenizer.from_pretrained(
            model_name, local_files_only=True, trust_remote_code=True
        )
        model = AutoModel.from_pretrained(
            model_name, local_files_only=True, trust_remote_code=True
        )

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)
        model.eval()
        print(f"Embedding model '{model_name}' loaded successfully on device: {device}")
        return tokenizer, model, device
    except Exception as e:
        print(f"ERROR: Failed to load model: {e}")
        raise  # Critical failure


def _average_pool(
    last_hidden_states: torch.Tensor, attention_mask: torch.Tensor
) -> torch.Tensor:
    """Helper function for pooling."""
    last_hidden = last_hidden_states.masked_fill(~attention_mask[..., None].bool(), 0.0)
    return last_hidden.sum(dim=1) / attention_mask.sum(dim=1)[..., None]


def compute_embeddings(
    texts: list[str],
    model_components: ModelComponents,
    batch_size: int = 32,  # Make configurable later if needed
    normalize: bool = True,
    e5_prefix: str | None = None,
) -> np.ndarray:
    """Computes embeddings for a list of texts using the provided model components."""
    tokenizer, model, device = model_components
    all_embeddings: list[np.ndarray] = []

    if e5_prefix:
        texts_to_embed = [f"{e5_prefix}{text}" for text in texts]
        print(f"Adding prefix '{e5_prefix}' to texts for embedding.")
    else:
        texts_to_embed = texts

    print(f"Computing embeddings for {len(texts_to_embed)} texts...")
    for i in tqdm(
        range(0, len(texts_to_embed), batch_size),
        desc="Computing Embeddings",
        leave=False,
    ):
        batch_texts = texts_to_embed[i : i + batch_size]
        try:
            batch_dict = tokenizer(
                batch_texts,
                max_length=512,
                padding=True,
                truncation=True,
                return_tensors="pt",
            ).to(device)
        except Exception as e:
            print(f"ERROR: Tokenization failed for batch starting at index {i}: {e}")
            raise

        with torch.no_grad():
            try:
                outputs = model(**batch_dict)
                embeddings = _average_pool(
                    outputs.last_hidden_state, batch_dict["attention_mask"]
                )
            except Exception as e:
                print(
                    f"ERROR: Model inference failed for batch starting at index {i}: {e}"
                )
                raise

        if normalize:
            embeddings = F.normalize(embeddings, p=2, dim=1)

        all_embeddings.append(embeddings.cpu().numpy())

    if not all_embeddings:
        print("Warning: No embeddings generated.")
        # Determine embedding dimension dynamically or return empty array of correct shape if possible
        # Example: get embedding dim from model config if loaded
        # embedding_dim = model.config.hidden_size
        # return np.empty((0, embedding_dim), dtype=np.float32)
        # Fallback for now:
        return np.empty((0, 0), dtype=np.float32)

    final_embeddings = np.vstack(all_embeddings)
    print(f"Embeddings computed. Shape: {final_embeddings.shape}")
    return final_embeddings
