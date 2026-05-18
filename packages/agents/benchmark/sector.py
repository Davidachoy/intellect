"""Sector benchmark helpers — cross-company filters and response formatting."""

from __future__ import annotations

import random
from typing import Any

from query_router.registry import AGENT_REGISTRY, AgentRegistryEntry, lookup_company

ACME_COMPANY_ID = "a0000000-0000-4000-8000-000000000001"

# Italy-sector demo: map a single region filter to each company's comparable geography.
_ITALY_SECTOR_FILTERS: dict[str, dict[str, str]] = {
    ACME_COMPANY_ID: {"region": "Italy", "status": "active"},
    "a0000000-0000-4000-8000-000000000002": {"region": "Southern Europe"},
    "a0000000-0000-4000-8000-000000000003": {"region": "Western Europe"},
}

_BENCHMARK_NOISE_MEAN = -1.0
_BENCHMARK_NOISE_SCALE = 1.2


def resolve_focal_company(
    *,
    raw_query: str,
    mentioned_companies: list[str] | None,
    target_company_id: str | None = None,
) -> AgentRegistryEntry:
    """Pick the company being compared (defaults to Acme for demo)."""
    if mentioned_companies:
        for name in mentioned_companies:
            lower = name.lower()
            for entry in AGENT_REGISTRY:
                if entry.company_name.lower() == lower:
                    return entry
    if target_company_id:
        entry = lookup_company(target_company_id)
        if entry:
            return entry
    lower = raw_query.lower()
    for entry in AGENT_REGISTRY:
        if entry.company_name.lower() in lower:
            return entry
    return AGENT_REGISTRY[0]


def sector_filters_for_company(
    company_id: str,
    base_filters: dict[str, str],
) -> dict[str, str]:
    """Normalize region filters so all three demo companies contribute to the sector."""
    region = (base_filters.get("region") or "").strip()
    if region.lower() == "italy":
        mapped = _ITALY_SECTOR_FILTERS.get(company_id)
        if mapped:
            return dict(mapped)
    return dict(base_filters)


def apply_benchmark_dp_noise(value: float, *, rng: random.Random | None = None) -> int:
    """Gaussian noise on one company's aggregate count before sector roll-up."""
    source = rng or random
    noisy = value + source.gauss(_BENCHMARK_NOISE_MEAN, _BENCHMARK_NOISE_SCALE)
    return max(0, int(round(noisy)))


def format_benchmark_response(
    *,
    sector_average: int,
    focal_company_name: str,
    pct_vs_sector: int,
    region_label: str,
    metric_label: str = "active clients",
) -> str:
    direction = "above" if pct_vs_sector >= 0 else "below"
    pct_abs = abs(pct_vs_sector)
    return (
        f"Sector average: {sector_average} {metric_label} in {region_label}. "
        f"{focal_company_name} is {pct_abs}% {direction} sector average. "
        "Individual company results: private."
    )


def build_benchmark_insight(
    *,
    sector_average: int,
    pct_vs_sector: int,
    focal_company_name: str,
    region_label: str,
    domain: str,
    company_count: int,
    filters: dict[str, Any],
) -> dict[str, Any]:
    return {
        "aggregation": "benchmark",
        "intent": "benchmark",
        "domain": domain,
        "filters": filters,
        "value": sector_average,
        "metric": "sector_average",
        "region": region_label,
        "focal_company": focal_company_name,
        "pct_vs_sector": pct_vs_sector,
        "company_count": company_count,
        "extra": {"individual_results": "private"},
    }
