"""Cross-company benchmark aggregation with per-company differential privacy noise."""

from __future__ import annotations

import random
from typing import Any

from intelligence.base import IntelligenceAgent
from loguru import logger
from query_router.registry import AGENT_REGISTRY
from shared.models.routing import StructuredQuery

_BENCHMARK_NOISE_SCALE = 0.5


def _extract_numeric_value(insights: list[dict[str, Any]]) -> float | None:
    for insight in insights:
        value = insight.get("value")
        if isinstance(value, (int, float)):
            return float(value)
        extra = insight.get("extra") or {}
        if isinstance(extra.get("value"), (int, float)):
            return float(extra["value"])
    return None


def _apply_dp_noise(value: float) -> float:
    return value + random.gauss(0, _BENCHMARK_NOISE_SCALE)


async def aggregate_sector_benchmark(
    structured_query: StructuredQuery | dict[str, Any],
) -> dict[str, object]:
    """Query all registered companies; return sector average without per-company breakdown."""
    if isinstance(structured_query, StructuredQuery):
        structured = structured_query
    else:
        structured = StructuredQuery.model_validate(structured_query)

    noisy_values: list[float] = []
    total_records = 0

    for entry in AGENT_REGISTRY:
        try:
            result = await IntelligenceAgent(entry.company_id, structured).run()
        except Exception as exc:
            logger.warning(
                "benchmark: skip company={} error={}",
                entry.company_name,
                exc,
            )
            continue

        insight_dicts = [
            i.model_dump() if hasattr(i, "model_dump") else dict(i)
            for i in result.raw_insights
        ]
        value = _extract_numeric_value(insight_dicts)
        counts = result.record_counts or []
        total_records += sum(counts)

        if value is not None:
            noisy_values.append(_apply_dp_noise(value))

    company_count = len(noisy_values)
    if company_count == 0:
        return {
            "raw_insights": [],
            "record_counts": [],
            "response": (
                "Unable to compute sector benchmark — no aggregated metrics available "
                "across registered companies."
            ),
        }

    sector_avg = sum(noisy_values) / company_count
    metric = structured.aggregation or "metric"
    response = (
        f"Sector average {metric}: {sector_avg:.2f} "
        f"(based on {company_count} companies, individual results private)"
    )

    insight = {
        "aggregation": "benchmark",
        "intent": "benchmark",
        "domain": structured.domain,
        "value": round(sector_avg, 2),
        "metric": metric,
        "company_count": company_count,
        "extra": {"total_records": total_records, "dp_noise_applied": True},
    }

    return {
        "raw_insights": [insight],
        "record_counts": [max(total_records, 10)],
        "response": response,
    }
