"""Query embeddings for RAG (OpenAI or Gemini via LiteLLM)."""

from __future__ import annotations

from litellm import aembedding
from loguru import logger

from litellm_retry import with_litellm_retry
from model_registry import (
    attribution_from_invocation,
    configured_model_for_node,
    ensure_env_loaded,
    log_attribution,
)

EMBEDDING_DIMENSIONS = 768


def _embedding_model() -> str:
    ensure_env_loaded()
    return configured_model_for_node("embeddings") or "text-embedding-3-small"


async def embed_text(text: str) -> list[float]:
    """Embed a single query string via LiteLLM (OpenAI or Gemini)."""
    vectors = await embed_texts([text], batch_size=1)
    return vectors[0]


async def embed_texts(
    texts: list[str],
    *,
    batch_size: int = 128,
) -> list[list[float]]:
    """Embed many strings in batches via LiteLLM (OpenAI or Gemini)."""
    if not texts:
        return []

    model = _embedding_model()
    normalized = [t.strip() if t.strip() else " " for t in texts]
    vectors: list[list[float]] = []

    for start in range(0, len(normalized), batch_size):
        batch = normalized[start : start + batch_size]
        logger.debug(
            "Embedding batch model={} size={} offset={}",
            model,
            len(batch),
            start,
        )

        async def _call(inputs: list[str] = batch) -> object:
            return await aembedding(
                model=model,
                input=inputs,
                dimensions=EMBEDDING_DIMENSIONS,
            )

        response = await with_litellm_retry(_call)
        entry = attribution_from_invocation("embeddings", model=model, backend="litellm")
        log_attribution(entry)

        ordered = sorted(response.data, key=lambda row: row.get("index", 0))
        for row in ordered:
            vector = list(row["embedding"])
            if len(vector) != EMBEDDING_DIMENSIONS:
                logger.warning(
                    "Unexpected embedding size {} (expected {})",
                    len(vector),
                    EMBEDDING_DIMENSIONS,
                )
            vectors.append(vector)

    return vectors
