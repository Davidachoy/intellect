"""Cross-company benchmark aggregation with per-company differential privacy noise."""

from __future__ import annotations

from typing import Any

from benchmark.sector import (
    apply_benchmark_dp_noise,
    build_benchmark_insight,
    format_benchmark_response,
    resolve_focal_company,
    sector_filters_for_company,
)
from intelligence.base import IntelligenceAgent
from loguru import logger
from query_router.registry import AGENT_REGISTRY
from shared.constants import K_ANONYMITY_THRESHOLD
from shared.models.routing import StructuredQuery


def _extract_count(insights: list[dict[str, Any]]) -> int | None:
    for insight in insights:
        value = insight.get("value")
        if isinstance(value, (int, float)):
            return int(value)
        extra = insight.get("extra") or {}
        if isinstance(extra.get("record_count"), (int, float)):
            return int(extra["record_count"])
    return None


def _metric_label(filters: dict[str, str]) -> str:
    if filters.get("status") == "active":
        return "active clients"
    return "records"


async def aggregate_sector_benchmark(
    structured_query: StructuredQuery | dict[str, Any],
    *,
    raw_query: str = "",
    target_company_id: str | None = None,
    mentioned_companies: list[str] | None = None,
) -> dict[str, object]:
    """Query all registered companies; return sector average without per-company breakdown."""
    if isinstance(structured_query, StructuredQuery):
        structured = structured_query
    else:
        structured = StructuredQuery.model_validate(structured_query)

    base_filters = dict(structured.filters)
    if base_filters.get("region", "").lower() == "italy":
        base_filters.setdefault("status", "active")
    region_label = base_filters.get("region") or "the selected region"
    focal = resolve_focal_company(
        raw_query=raw_query,
        mentioned_companies=mentioned_companies,
        target_company_id=target_company_id,
    )

    per_company_raw: dict[str, int] = {}
    per_company_records: list[int] = []

    benchmark_sq = structured.model_copy(
        update={
            "intent": "benchmark",
            "aggregation": "count",
        }
    )

    for entry in AGENT_REGISTRY:
        company_filters = sector_filters_for_company(entry.company_id, base_filters)
        company_query = benchmark_sq.model_copy(update={"filters": company_filters})
        try:
            result = await IntelligenceAgent(
                entry.company_id,
                company_query,
                use_vector_scope=False,
            ).run()
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
        count = _extract_count(insight_dicts)
        branch_records = result.record_counts or []
        if count is None and branch_records:
            count = max(branch_records)
        if count is None:
            continue

        per_company_raw[entry.company_id] = count
        per_company_records.append(max(branch_records) if branch_records else count)

    if len(per_company_raw) < 2:
        return {
            "raw_insights": [],
            "record_counts": [],
            "response": (
                "Unable to compute sector benchmark — need aggregated metrics from "
                "at least two registered companies."
            ),
        }

    noisy_values = [
        apply_benchmark_dp_noise(float(value)) for value in per_company_raw.values()
    ]
    sector_average = int(round(sum(noisy_values) / len(noisy_values)))

    focal_raw = per_company_raw.get(focal.company_id)
    if focal_raw is None:
        focal_raw = next(iter(per_company_raw.values()))

    if sector_average <= 0:
        pct_vs_sector = 0
    else:
        pct_vs_sector = int(
            round((focal_raw - sector_average) / sector_average * 100)
        )

    response = format_benchmark_response(
        sector_average=sector_average,
        focal_company_name=focal.company_name,
        pct_vs_sector=pct_vs_sector,
        region_label=region_label,
        metric_label=_metric_label(base_filters),
    )

    insight = build_benchmark_insight(
        sector_average=sector_average,
        pct_vs_sector=pct_vs_sector,
        focal_company_name=focal.company_name,
        region_label=region_label,
        domain=structured.domain,
        company_count=len(per_company_raw),
        filters=base_filters,
    )

    k_safe_counts = [
        max(K_ANONYMITY_THRESHOLD, c) for c in per_company_records if c > 0
    ]
    if not k_safe_counts:
        k_safe_counts = [K_ANONYMITY_THRESHOLD * len(per_company_raw)]

    return {
        "raw_insights": [insight],
        "record_counts": k_safe_counts,
        "response": response,
        "target_company_id": focal.company_id,
    }
