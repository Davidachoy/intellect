"""Map aggregate RPC payloads to privacy-safe insight dicts."""

from __future__ import annotations

from typing import Any

from shared.models.intelligence import AggregatedInsight, IntelligenceRunResult
from shared.models.routing import StructuredQuery

_RAW_ROW_KEYS = frozenset(
    {
        "age",
        "ltv_usd",
        "value_usd",
        "gs",
        "content",
        "embedding",
        "document_id",
        "id",
    }
)


def _assert_no_raw_rows(insight: dict[str, Any]) -> None:
    for key in insight:
        if key in _RAW_ROW_KEYS:
            raise ValueError(f"Insight must not expose raw field: {key}")
    for group in insight.get("groups") or []:
        if isinstance(group, dict):
            for key in group:
                if key in _RAW_ROW_KEYS:
                    raise ValueError(f"Grouped insight must not expose raw field: {key}")


def aggregate_payload_to_insight(
    payload: dict[str, Any],
    structured: StructuredQuery,
) -> AggregatedInsight:
    aggregation = str(payload.get("aggregation") or structured.aggregation)
    record_count = int(payload.get("record_count") or 0)

    if aggregation == "count":
        insight = AggregatedInsight(
            aggregation="count",
            intent=structured.intent,
            domain=structured.domain,
            filters=structured.filters,
            value=record_count,
            metric="record_count",
        )
    elif aggregation == "average":
        insight = AggregatedInsight(
            aggregation="average",
            intent=structured.intent,
            domain=structured.domain,
            filters=structured.filters,
            value=payload.get("value"),
            metric=str(payload.get("metric") or "value"),
            extra={"record_count": record_count},
        )
    elif aggregation == "percentage":
        insight = AggregatedInsight(
            aggregation="percentage",
            intent=structured.intent,
            domain=structured.domain,
            filters=structured.filters,
            value=payload.get("value"),
            metric="percentage",
            extra={
                "denominator_count": payload.get("denominator_count"),
                "record_count": record_count,
            },
        )
    elif aggregation == "group_by_region":
        groups = payload.get("groups") or []
        if isinstance(groups, str):
            groups = []
        insight = AggregatedInsight(
            aggregation="group_by_region",
            intent=structured.intent,
            domain=structured.domain,
            filters=structured.filters,
            groups=list(groups) if isinstance(groups, list) else [],
            value=record_count,
            metric="record_count",
        )
    else:
        insight = AggregatedInsight(
            aggregation=aggregation,
            intent=structured.intent,
            domain=structured.domain,
            filters=structured.filters,
            value=payload.get("value"),
            extra={"record_count": record_count, "raw_payload": payload},
        )

    dumped = insight.model_dump(exclude_none=True)
    _assert_no_raw_rows(dumped)
    return insight


def collect_record_counts(insights: list[AggregatedInsight]) -> list[int]:
    counts: list[int] = []
    for insight in insights:
        if insight.aggregation == "group_by_region":
            for group in insight.groups:
                if isinstance(group, dict) and "record_count" in group:
                    counts.append(int(group["record_count"]))
        elif insight.aggregation == "count" and insight.value is not None:
            counts.append(int(insight.value))
        elif insight.extra.get("record_count") is not None:
            counts.append(int(insight.extra["record_count"]))
    return [c for c in counts if c > 0]


def build_run_result(insights: list[AggregatedInsight]) -> IntelligenceRunResult:
    raw = [i.model_dump(exclude_none=True) for i in insights]
    for item in raw:
        _assert_no_raw_rows(item)
    return IntelligenceRunResult(
        raw_insights=raw,
        record_counts=collect_record_counts(insights),
    )
