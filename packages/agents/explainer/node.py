"""Query Explainer — plain-English derivation after Intelligence, before Pricing."""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from litellm import acompletion
from loguru import logger

from explainer.prompts import EXPLAINER_SYSTEM_PROMPT, EXPLAINER_USER_TEMPLATE
from litellm_retry import with_litellm_retry
from model_registry import (
    GEMINI_DEFAULT_FLASH,
    attribution_from_invocation,
    log_attribution,
)
from state import QueryState

_DEFAULT_EXPLAINER_MODEL = GEMINI_DEFAULT_FLASH


def _ensure_env() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    load_dotenv(repo_root / ".env", override=False)


def _explainer_model() -> str:
    _ensure_env()
    return os.getenv("EXPLAINER_MODEL", "").strip() or os.getenv(
        "ROUTER_MODEL", ""
    ).strip() or _DEFAULT_EXPLAINER_MODEL


async def _generate_explanation(
    *,
    structured_query: dict,
    raw_insights: list[dict],
    record_counts: list[int],
) -> tuple[str, dict[str, object]]:
    model = _explainer_model()
    user_content = EXPLAINER_USER_TEMPLATE.format(
        structured_query=json.dumps(structured_query, default=str),
        raw_insights=json.dumps(raw_insights[:5], default=str),
        record_counts=record_counts,
    )

    async def _call() -> object:
        return await acompletion(
            model=model,
            messages=[
                {"role": "system", "content": EXPLAINER_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
        )

    response = await with_litellm_retry(_call)
    text = (response.choices[0].message.content or "").strip()
    attribution = attribution_from_invocation(
        "explainer", model=model, backend="litellm"
    )
    log_attribution(attribution)
    return text, attribution.model_dump()


def _heuristic_explanation(
    structured_query: dict,
    raw_insights: list[dict],
    record_counts: list[int],
) -> str:
    total_records = sum(record_counts) if record_counts else 0
    filters = structured_query.get("filters") or {}
    filter_bits = ", ".join(f"{k}={v}" for k, v in filters.items() if v)
    filter_text = f" ({filter_bits})" if filter_bits else ""
    if total_records > 0:
        return (
            f"This answer is based on {total_records} aggregated records"
            f"{filter_text}, derived from the structured query intent "
            f"'{structured_query.get('intent', 'unknown')}'."
        )
    if raw_insights:
        first = raw_insights[0]
        count = first.get("record_count") or first.get("extra", {}).get("record_count")
        if count:
            return (
                f"This answer reflects {count} records matching the applied filters"
                f"{filter_text}."
            )
    return "This answer was derived from aggregated intelligence over the company's private data."


async def explainer_node(state: QueryState) -> dict[str, object]:
    structured = state.get("structured_query") or {}
    raw_insights = list(state.get("raw_insights") or [])
    record_counts = list(state.get("record_counts") or [])
    attribution_map = dict(state.get("model_attribution") or {})

    if state.get("error") or not raw_insights:
        explanation = ""
        return {"explanation": explanation, "model_attribution": attribution_map}

    try:
        explanation, attr = await _generate_explanation(
            structured_query=structured,
            raw_insights=raw_insights,
            record_counts=record_counts,
        )
        attribution_map["explainer"] = attr
    except Exception as exc:
        logger.warning("explainer: LLM failed ({}), using heuristic", exc)
        explanation = _heuristic_explanation(structured, raw_insights, record_counts)

    logger.info("explainer: query_id={} chars={}", state["query_id"], len(explanation))
    return {"explanation": explanation, "model_attribution": attribution_map}
