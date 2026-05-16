"""Rule-based query router — no external API, for local demo and Gemini outages."""

from __future__ import annotations

import re

from loguru import logger

from query_router.models import LLMRouterOutput, LLMSubQuery
from query_router.registry import AGENT_REGISTRY

_REGION_KEYWORDS: dict[str, str] = {
    "italy": "Italy",
    "italian": "Italy",
    "germany": "Germany",
    "nordics": "Nordics",
    "nordic": "Nordics",
}

_STATUS_KEYWORDS: dict[str, str] = {
    "active": "active",
    "delayed": "delayed",
}


def _mentioned_companies(text: str) -> list[str]:
    lower = text.lower()
    found: list[str] = []
    for entry in AGENT_REGISTRY:
        if entry.company_name.lower() in lower:
            found.append(entry.company_name)
    return found


def _extract_region_filters(text: str) -> dict[str, str]:
    lower = text.lower()
    for keyword, canonical in _REGION_KEYWORDS.items():
        if keyword in lower:
            return {"region": canonical}
    return {}


def _extract_status_filters(text: str) -> dict[str, str]:
    lower = text.lower()
    for keyword, status in _STATUS_KEYWORDS.items():
        if keyword in lower:
            return {"status": status}
    return {}


def _extract_segment_filters(text: str) -> dict[str, str]:
    lower = text.lower()
    if "premium" in lower:
        return {"segment": "premium"}
    return {}


def _extract_outcome_filters(text: str) -> dict[str, str]:
    lower = text.lower()
    if "positive" in lower and ("outcome" in lower or "trial" in lower):
        return {"outcome": "positive"}
    return {}


def _detect_domain(text: str) -> str:
    lower = text.lower()
    if any(
        word in lower
        for word in ("trial", "clinical", "participant", "outcome", "enrollment")
    ):
        return "clinical_trials"
    if any(
        word in lower
        for word in ("shipment", "logistics", "freight", "delivery", "shipments")
    ):
        return "logistics_shipments"
    if any(word in lower for word in ("ltv", "segment", "retail")):
        return "retail_customers"
    return "customers"


def _detect_intent_and_aggregation(text: str) -> tuple[str, str]:
    lower = text.lower()
    if "how many" in lower or re.search(r"\bcount\b", lower):
        return "count", "count"
    if "average" in lower or "avg" in lower or "ltv" in lower:
        return "average", "average"
    if "percentage" in lower or "percent" in lower:
        return "percentage", "percentage"
    return "count", "count"


def _build_filters(text: str) -> dict[str, str]:
    filters: dict[str, str] = {}
    filters.update(_extract_region_filters(text))
    filters.update(_extract_status_filters(text))
    filters.update(_extract_segment_filters(text))
    filters.update(_extract_outcome_filters(text))
    return filters


def _parse_single_clause(text: str) -> LLMRouterOutput:
    intent, aggregation = _detect_intent_and_aggregation(text)
    return LLMRouterOutput(
        intent=intent,
        filters=_build_filters(text),
        aggregation=aggregation,
        domain=_detect_domain(text),
        mentioned_companies=_mentioned_companies(text),
        complexity="simple",
        sub_queries=[],
    )


def _split_compound(raw_query: str) -> list[str] | None:
    """Split compare / compound queries on ' and ' or ' with '."""
    text = raw_query.strip()
    lower = text.lower()

    if re.search(r"\s+with\s+", text, flags=re.IGNORECASE):
        parts = re.split(r"\s+with\s+", text, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) == 2:
            left, right = (p.strip() for p in parts)
            if len(left) >= 8 and len(right) >= 8:
                if left.lower().startswith("compare "):
                    left = left[8:].strip()
                return [left, right]

    if " and " in lower:
        parts = re.split(r"\s+and\s+", text, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) == 2:
            left, right = (p.strip() for p in parts)
            if len(left) >= 8 and len(right) >= 8:
                return [left, right]

    return None


async def generate_heuristic_router_output(raw_query: str) -> LLMRouterOutput:
    """Parse NL query with keyword rules (demo-safe, offline)."""
    query = raw_query.strip()
    logger.debug("Heuristic router parsing query (len={})", len(query))

    parts = _split_compound(query)
    if parts is None:
        return _parse_single_clause(query)

    sub_outputs = [_parse_single_clause(part) for part in parts]
    primary = sub_outputs[0]
    sub_queries = [
        LLMSubQuery(
            intent=sub.intent,
            filters=sub.filters,
            aggregation=sub.aggregation,
            domain=sub.domain,
        )
        for sub in sub_outputs
    ]

    mentioned: list[str] = []
    for sub in sub_outputs:
        for name in sub.mentioned_companies:
            if name not in mentioned:
                mentioned.append(name)

    return LLMRouterOutput(
        intent="compare" if len(sub_outputs) > 1 else primary.intent,
        filters=primary.filters,
        aggregation=primary.aggregation,
        domain=primary.domain,
        mentioned_companies=mentioned,
        complexity="compound",
        sub_queries=sub_queries,
    )
