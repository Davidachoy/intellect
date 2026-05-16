"""Sensitivity tier definitions and cost calculation."""

from __future__ import annotations

from shared.constants import DEFAULT_SENSITIVITY_TIER, SENSITIVITY_TIERS

# Re-export for callers that import TIERS from pricing.tiers
TIERS = SENSITIVITY_TIERS
DEFAULT_TIER = DEFAULT_SENSITIVITY_TIER

_DOMAIN_TIER_HINTS: tuple[tuple[str, str], ...] = (
    ("clinical", "strategic"),
    ("customer", "sensitive"),
    ("retail", "sensitive"),
    ("logistic", "aggregated"),
    ("shipment", "aggregated"),
)


def cost_for_tier(tier: str) -> float:
    """Return base USD cost for a sensitivity tier."""
    return SENSITIVITY_TIERS.get(tier, SENSITIVITY_TIERS[DEFAULT_TIER])


def resolve_sensitivity_tier(structured_query: dict | None) -> str:
    """Infer sensitivity tier from router structured_query."""
    sq = structured_query or {}
    intent = sq.get("intent", "")
    if intent == "unsupported":
        return "public"

    sub_queries = sq.get("sub_queries") or []
    if len(sub_queries) > 1:
        return "strategic"

    domain = (sq.get("domain") or "").lower()
    for hint, tier in _DOMAIN_TIER_HINTS:
        if hint in domain:
            return tier

    return DEFAULT_TIER


def calculate_cost(
    sensitivity_tier: str,
    structured_query: dict | None = None,
) -> float:
    """Cost from tier; compound queries multiply by sub-query count."""
    base = cost_for_tier(sensitivity_tier)
    sub_queries = (structured_query or {}).get("sub_queries") or []
    if len(sub_queries) > 1:
        return round(base * len(sub_queries), 6)
    return base
