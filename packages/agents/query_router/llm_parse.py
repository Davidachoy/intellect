"""Parse JSON router responses from LLM text (with optional markdown fences)."""

from __future__ import annotations

import json
import re
from typing import Any

from loguru import logger
from pydantic import ValidationError

from query_router.models import LLMRouterOutput, LLMSubQuery

_JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)

OUT_OF_SCOPE_INTENT = "unsupported"
OUT_OF_SCOPE_DOMAIN = "none"


def out_of_scope_router_output(*, reason: str = "not_business_intelligence") -> LLMRouterOutput:
    return LLMRouterOutput(
        intent=OUT_OF_SCOPE_INTENT,
        filters={"reason": reason},
        aggregation="none",
        domain=OUT_OF_SCOPE_DOMAIN,
    )


def is_out_of_scope_output(output: LLMRouterOutput) -> bool:
    return output.intent == OUT_OF_SCOPE_INTENT or output.domain == OUT_OF_SCOPE_DOMAIN


def _coerce_router_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Repair common LLM shapes (compound JSON missing top-level intent/domain)."""
    if not isinstance(payload, dict):
        return None

    intent = payload.get("intent")
    aggregation = payload.get("aggregation")
    domain = payload.get("domain")
    if intent and aggregation and domain:
        return payload

    sub_raw = payload.get("sub_queries") or []
    subs: list[LLMSubQuery] = []
    for item in sub_raw:
        if isinstance(item, dict):
            try:
                subs.append(LLMSubQuery.model_validate(item))
            except ValidationError:
                continue

    if not subs:
        return None

    primary = subs[0]
    mentioned = list(payload.get("mentioned_companies") or [])
    complexity = payload.get("complexity") or "compound"
    intent_val = intent or ("compare" if complexity == "compound" else primary.intent)
    return {
        "intent": intent_val,
        "filters": payload.get("filters") or primary.filters,
        "aggregation": aggregation or primary.aggregation,
        "domain": domain or primary.domain,
        "mentioned_companies": mentioned,
        "complexity": complexity,
        "sub_queries": [s.model_dump() for s in subs],
    }


def parse_router_json(text: str) -> LLMRouterOutput:
    stripped = text.strip()
    fence = _JSON_FENCE.search(stripped)
    if fence:
        stripped = fence.group(1).strip()

    if not stripped or stripped == "{}":
        logger.warning("Router LLM returned empty JSON; treating as out-of-scope")
        return out_of_scope_router_output(reason="empty_llm_response")

    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        logger.warning("Router LLM returned non-JSON; treating as out-of-scope")
        return out_of_scope_router_output(reason="invalid_json")

    if not isinstance(payload, dict):
        return out_of_scope_router_output(reason="invalid_json_shape")

    try:
        return LLMRouterOutput.model_validate(payload)
    except ValidationError as exc:
        coerced = _coerce_router_payload(payload)
        if coerced:
            logger.info("Router JSON coerced from partial compound payload")
            return LLMRouterOutput.model_validate(coerced)
        logger.warning("Router JSON failed validation ({}); treating as out-of-scope", exc)
        return out_of_scope_router_output(reason="incomplete_json")
