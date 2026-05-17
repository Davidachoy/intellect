"""Query embeddings for RAG via Gemini Embedding API."""

from __future__ import annotations

from loguru import logger

from gemini_client import (
    GEMINI_EMBEDDING_DIMENSIONS,
    GEMINI_EMBEDDING_MODEL,
    embed_gemini_texts,
)
from gemini_retry import with_gemini_retry
from model_registry import (
    attribution_from_invocation,
    configured_model_for_node,
    ensure_env_loaded,
    log_attribution,
)

EMBEDDING_DIMENSIONS = GEMINI_EMBEDDING_DIMENSIONS


def _embedding_model() -> str:
    ensure_env_loaded()
    return configured_model_for_node("embeddings") or GEMINI_EMBEDDING_MODEL


async def embed_text(text: str) -> list[float]:
    """Embed a single query string via Gemini."""
    vectors = await embed_texts([text], batch_size=1)
    return vectors[0]


async def embed_texts(
    texts: list[str],
    *,
    batch_size: int = 128,
) -> list[list[float]]:
    """Embed many strings in batches via Gemini."""
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

        async def _call(inputs: list[str] = batch) -> list[list[float]]:
            return await embed_gemini_texts(
                model=model,
                texts=inputs,
                output_dimensionality=EMBEDDING_DIMENSIONS,
            )

        batch_vectors = await with_gemini_retry(_call)
        entry = attribution_from_invocation("embeddings", model=model, backend="google-genai")
        log_attribution(entry)

        for vector in batch_vectors:
            if len(vector) != EMBEDDING_DIMENSIONS:
                logger.warning(
                    "Unexpected embedding size {} (expected {})",
                    len(vector),
                    EMBEDDING_DIMENSIONS,
                )
            vectors.append(vector)

    return vectors
