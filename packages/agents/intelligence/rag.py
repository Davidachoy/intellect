"""RAG pipeline: embed query, pgvector scope, aggregate-only SQL."""

from __future__ import annotations

from typing import Any

from loguru import logger

from intelligence.aggregates import aggregate_payload_to_insight, build_run_result
from intelligence.embeddings import embed_text
from intelligence.store import match_document_ids, metric_field_for_domain, run_aggregate
from shared.constants import K_ANONYMITY_THRESHOLD
from shared.models.intelligence import IntelligenceRunResult
from shared.models.routing import StructuredQuery

AGGREGATION_ALIASES: dict[str, str] = {
    "sum": "count",
    "group": "group_by_region",
    "group_by_region": "group_by_region",
    "group_by": "group_by_region",
}


def _normalize_aggregation(aggregation: str) -> str:
    key = aggregation.strip().lower()
    return AGGREGATION_ALIASES.get(key, key)


def _query_text_for_embedding(structured: StructuredQuery) -> str:
    parts = [
        structured.intent,
        structured.aggregation,
        structured.domain,
    ]
    for key, value in sorted(structured.filters.items()):
        parts.append(f"{key}={value}")
    return " ".join(str(p) for p in parts if p)


def _record_count_from_payload(payload: dict[str, Any]) -> int:
    try:
        return int(payload.get("record_count") or 0)
    except (TypeError, ValueError):
        return 0


async def run_rag(
    company_id: str,
    structured: StructuredQuery,
    *,
    use_vector_scope: bool = True,
    match_count: int = 200,
) -> IntelligenceRunResult:
    """Embed, optionally narrow via pgvector, then aggregate (never raw rows)."""
    insights: list = []

    queries: list[StructuredQuery] = (
        structured.sub_queries if structured.sub_queries else [structured]
    )

    scope_ids: list[str] | None = None
    if use_vector_scope:
        try:
            query_text = _query_text_for_embedding(structured)
            embedding = await embed_text(query_text)
            matched = await match_document_ids(
                company_id,
                embedding,
                match_count=match_count,
            )
            if matched:
                scope_ids = matched
                logger.info(
                    "RAG vector scope company_id={} matched_docs={}",
                    company_id,
                    len(matched),
                )
            else:
                logger.info(
                    "RAG vector scope empty (no embeddings yet?) — metadata-only aggregate"
                )
        except Exception as exc:
            logger.warning("Vector scope skipped: {}", exc)

    metric_field = metric_field_for_domain(structured.domain)

    for sub in queries:
        aggregation = _normalize_aggregation(sub.aggregation)
        payload = await run_aggregate(
            company_id,
            aggregation,
            sub.filters,
            metric_field=metric_field,
            scope_ids=scope_ids,
        )
        if scope_ids and sub.filters and _record_count_from_payload(payload) < K_ANONYMITY_THRESHOLD:
            logger.info(
                "RAG vector scope below k-anonymity for filtered aggregate; "
                "retrying aggregate without vector scope"
            )
            payload = await run_aggregate(
                company_id,
                aggregation,
                sub.filters,
                metric_field=metric_field,
                scope_ids=None,
            )
        insight = aggregate_payload_to_insight(payload, sub)
        insights.append(insight)

    return build_run_result(insights)
