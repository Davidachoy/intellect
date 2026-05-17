"""Shared Google Gen AI SDK helpers for Gemini chat and embeddings."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

GEMINI_FLASH_MODEL = "gemini-3-flash-preview"
GEMINI_EMBEDDING_MODEL = "gemini-embedding-2"
GEMINI_EMBEDDING_DIMENSIONS = 768


def ensure_gemini_env_loaded() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    load_dotenv(repo_root / ".env", override=False)


def normalize_gemini_model(model: str | None, *, default: str = GEMINI_FLASH_MODEL) -> str:
    raw = (model or default).strip() or default
    for prefix in ("gemini/", "google/"):
        if raw.lower().startswith(prefix):
            return raw.split("/", 1)[1]
    if raw.lower().startswith("models/"):
        return raw.split("/", 1)[1]
    return raw


def is_gemini_model_name(model: str | None) -> bool:
    if not model:
        return False
    normalized = normalize_gemini_model(model)
    return normalized.startswith("gemini-")


def _api_key() -> str:
    ensure_gemini_env_loaded()
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is required for Gemini calls")
    return key


def _client() -> Any:
    from google import genai

    return genai.Client(api_key=_api_key())


async def generate_gemini_text(
    *,
    model: str,
    system_instruction: str,
    user_prompt: str,
    temperature: float,
    max_output_tokens: int | None = None,
    response_mime_type: str | None = None,
) -> str:
    from google.genai import types

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        response_mime_type=response_mime_type,
    )
    client = _client()
    response = await client.aio.models.generate_content(
        model=normalize_gemini_model(model),
        contents=user_prompt,
        config=config,
    )
    return (response.text or "").strip()


def _embedding_values(item: Any) -> list[float]:
    values = getattr(item, "values", None)
    if values is None and isinstance(item, dict):
        values = item.get("values") or item.get("embedding")
    if values is None:
        raise ValueError("Gemini embedding response did not include vector values")
    return [float(value) for value in values]


async def embed_gemini_texts(
    *,
    model: str,
    texts: list[str],
    output_dimensionality: int = GEMINI_EMBEDDING_DIMENSIONS,
) -> list[list[float]]:
    from google.genai import types

    config = types.EmbedContentConfig(output_dimensionality=output_dimensionality)
    contents = [
        types.Content(parts=[types.Part.from_text(text=text)])
        for text in texts
    ]
    client = _client()
    response = await client.aio.models.embed_content(
        model=normalize_gemini_model(model, default=GEMINI_EMBEDDING_MODEL),
        contents=contents,
        config=config,
    )

    embeddings = getattr(response, "embeddings", None)
    if embeddings is None:
        single = getattr(response, "embedding", None)
        embeddings = [single] if single is not None else None
    if embeddings is None:
        raise ValueError("Gemini embedding response did not include embeddings")

    return [_embedding_values(item) for item in embeddings]
