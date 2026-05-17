"""Router dispatch: Gemini model chain or heuristic fallback."""

from __future__ import annotations

import os

from loguru import logger

from gemini_client import GEMINI_FLASH_MODEL, is_gemini_model_name
from model_registry import (
    attribution_from_invocation,
    ensure_env_loaded,
    log_attribution,
)
from query_router.generation import RouterGenerationResult
from query_router.heuristic import generate_heuristic_router_output
from query_router.llm_parse import is_out_of_scope_output
from query_router.llm_router import generate_llm_router_output
from query_router.models import LLMRouterOutput

DEFAULT_MODEL_CHAIN: tuple[str, ...] = (GEMINI_FLASH_MODEL,)

_LEGACY_PROVIDER_MODELS: dict[str, str] = {
    "gemini": GEMINI_FLASH_MODEL,
    "google": GEMINI_FLASH_MODEL,
}

_HEURISTIC_ALIASES = frozenset({"heuristic", "rules", "local"})


def _parse_model_list(raw: str) -> list[str]:
    return [m.strip() for m in raw.split(",") if m.strip()]


def _dedupe_models(models: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for model in models:
        key = model.lower()
        if key not in seen:
            seen.add(key)
            ordered.append(model)
    return ordered


def _model_has_credentials(model: str) -> bool:
    return is_gemini_model_name(model) and bool(os.getenv("GEMINI_API_KEY", "").strip())


def _gemini_models_only(models: list[str]) -> list[str]:
    gemini_models: list[str] = []
    for model in models:
        if is_gemini_model_name(model):
            gemini_models.append(model)
        else:
            logger.warning(
                "Ignoring non-Gemini router model={!r}; this build supports Gemini only",
                model,
            )
    return gemini_models


def _router_mode() -> str:
    ensure_env_loaded()
    return (os.getenv("ROUTER_MODE") or os.getenv("ROUTER_PROVIDER") or "auto").strip().lower()


def resolve_model_chain(*, filter_missing_keys: bool = True) -> list[str]:
    ensure_env_loaded()
    mode = _router_mode()

    if mode in _HEURISTIC_ALIASES:
        return []

    primary = os.getenv("ROUTER_MODEL", "").strip()
    fallbacks = _parse_model_list(os.getenv("ROUTER_MODEL_FALLBACKS", ""))

    if not primary and mode in _LEGACY_PROVIDER_MODELS:
        primary = _LEGACY_PROVIDER_MODELS[mode]

    chain: list[str] = []
    if primary:
        chain.append(primary)
    chain.extend(fallbacks)
    if mode == "auto" and not chain:
        chain = list(DEFAULT_MODEL_CHAIN)
    elif not chain and mode not in ("auto", "") and mode not in _HEURISTIC_ALIASES:
        chain = [mode]

    chain = _dedupe_models(chain)
    chain = _gemini_models_only(chain)
    if mode == "auto" and not chain:
        chain = list(DEFAULT_MODEL_CHAIN)
    if filter_missing_keys and mode == "auto":
        chain = [m for m in chain if _model_has_credentials(m)]
    return chain


def _llm_error_should_fallback(exc: BaseException) -> bool:
    message = str(exc).lower()
    return any(
        token in message
        for token in (
            "429",
            "resource_exhausted",
            "quota",
            "billing",
            "limit: 0",
            "insufficient_quota",
            "rate_limit",
            "overloaded",
            "authentication",
            "invalid_api_key",
            "401",
            "403",
        )
    )


def _with_attribution(output: LLMRouterOutput, *, model: str | None, backend: str) -> RouterGenerationResult:
    entry = attribution_from_invocation("router", model=model, backend=backend)
    log_attribution(entry)
    return RouterGenerationResult(output=output, attribution=entry)


async def generate_router_output(raw_query: str) -> RouterGenerationResult:
    """Try ROUTER_MODEL chain via Gemini; fall back to heuristic on failure."""
    models = resolve_model_chain()
    if not models:
        logger.info("Using heuristic query router (no LLM models configured)")
        output = await generate_heuristic_router_output(raw_query)
        return _with_attribution(output, model=None, backend="heuristic")

    last_error: BaseException | None = None
    for model in models:
        try:
            logger.info("Routing with model={}", model)
            output = await generate_llm_router_output(raw_query, model=model)
            if is_out_of_scope_output(output) and output.filters.get("reason") == "incomplete_json":
                logger.info("LLM router incomplete JSON; using heuristic for this query")
                output = await generate_heuristic_router_output(raw_query)
                return _with_attribution(output, model=model, backend="heuristic")
            return _with_attribution(output, model=model, backend="google-genai")
        except Exception as exc:
            last_error = exc
            if not _llm_error_should_fallback(exc):
                raise
            logger.warning("Model {} unavailable ({}), trying next", model, exc)

    logger.warning(
        "All LLM models failed (last: {}), falling back to heuristic",
        last_error,
    )
    output = await generate_heuristic_router_output(raw_query)
    return _with_attribution(output, model=None, backend="heuristic")
