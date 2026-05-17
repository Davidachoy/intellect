"""Reconstruction-risk classification via Featherless."""

from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx
from loguru import logger

from model_registry import (
    FEATHERLESS_DEFAULT_PRIVACY_MODEL,
    attribution_from_invocation,
    configured_model_for_node,
    ensure_env_loaded,
    log_attribution,
)
from privacy_guard.checks import check_reconstruction
from privacy_guard.prompts import (
    RECONSTRUCTION_SYSTEM_PROMPT,
    RECONSTRUCTION_USER_TEMPLATE,
)
from shared.models.agent import ModelAttributionEntry

FEATHERLESS_BASE_URL = "https://api.featherless.ai/v1"
DEFAULT_PRIVACY_MODEL = FEATHERLESS_DEFAULT_PRIVACY_MODEL
_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _featherless_api_key() -> str | None:
    ensure_env_loaded()
    key = os.getenv("FEATHERLESS_API_KEY", "").strip()
    return key or None


def _privacy_backend() -> str:
    ensure_env_loaded()
    explicit = os.getenv("PRIVACY_GUARD_BACKEND", "").strip().lower()
    if explicit in ("heuristic", "rules", "local"):
        return "heuristic"
    if explicit == "featherless":
        return "featherless"
    if _featherless_api_key():
        return "featherless"
    return "heuristic"


def _privacy_model() -> str:
    return configured_model_for_node("privacy_guard") or DEFAULT_PRIVACY_MODEL


def _strip_json_fences(text: str) -> str:
    return _JSON_FENCE_RE.sub("", text.strip()).strip()


def _parse_reconstruction_payload(text: str) -> dict[str, Any]:
    cleaned = _strip_json_fences(text)
    return json.loads(cleaned)


def _interpret_payload(
    parsed: dict[str, Any], *, model: str | None, backend: str
) -> tuple[bool, str | None, ModelAttributionEntry]:
    is_reconstruction = bool(parsed.get("is_reconstruction"))
    reason_text = str(parsed.get("reason") or "").strip()
    entry = attribution_from_invocation("privacy_guard", model=model, backend=backend)
    log_attribution(entry)
    if is_reconstruction:
        block = reason_text or "Query appears designed to reconstruct individual records"
        return False, block, entry
    return True, None, entry


def _heuristic_fallback(query: str, *, model: str | None, backend: str) -> tuple[bool, str | None, ModelAttributionEntry]:
    safe = check_reconstruction(query)
    entry = attribution_from_invocation("privacy_guard", model=model, backend=backend)
    log_attribution(entry)
    reason = None if safe else "Query appears designed to reconstruct individual records"
    return safe, reason, entry


async def _classify_with_featherless(query: str) -> tuple[bool, str | None, ModelAttributionEntry]:
    api_key = _featherless_api_key()
    model = _privacy_model()
    if not api_key:
        return _heuristic_fallback(query, model=None, backend="heuristic")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": RECONSTRUCTION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": RECONSTRUCTION_USER_TEMPLATE.format(query=query.strip()),
            },
        ],
        "temperature": 0.0,
        "max_tokens": 256,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{FEATHERLESS_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
        text = body["choices"][0]["message"]["content"]
        parsed = _parse_reconstruction_payload(text)
        return _interpret_payload(parsed, model=model, backend="featherless")
    except Exception as exc:
        logger.warning("Featherless reconstruction check failed ({}), using heuristic", exc)
        return _heuristic_fallback(query, model=model, backend="heuristic")


async def classify_reconstruction_with_featherless(
    query: str,
) -> tuple[bool, str | None, ModelAttributionEntry]:
    """
    Return (is_safe, block_reason, attribution).
    is_safe is True when the query is not a reconstruction attempt.
    """
    backend = _privacy_backend()
    if backend == "featherless":
        return await _classify_with_featherless(query)
    logger.warning("FEATHERLESS_API_KEY missing; using heuristic reconstruction check")
    return _heuristic_fallback(query, model=None, backend="heuristic")
