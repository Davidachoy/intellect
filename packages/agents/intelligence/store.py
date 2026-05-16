"""Supabase/pgvector access for Intelligence Agent — aggregate-only RPCs."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from loguru import logger

from db.client import get_supabase_client

ACME_RETAIL_COMPANY_ID = "a0000000-0000-4000-8000-000000000001"

METRIC_FIELDS_BY_DOMAIN: dict[str, str] = {
    "customers": "ltv_usd",
    "retail_customers": "ltv_usd",
    "shipments": "value_usd",
    "logistics_shipments": "value_usd",
    "clinical_trials": "outcome",
}


def metric_field_for_domain(domain: str) -> str:
    return METRIC_FIELDS_BY_DOMAIN.get(domain, "ltv_usd")


async def match_document_ids(
    company_id: str,
    query_embedding: list[float],
    *,
    match_count: int = 200,
) -> list[str]:
    """Vector similarity search; returns document ids only (not row payloads)."""
    client = await get_supabase_client()
    response = await client.rpc(
        "match_company_documents",
        {
            "p_company_id": company_id,
            "query_embedding": query_embedding,
            "match_count": match_count,
        },
    ).execute()

    rows = response.data or []
    ids = [str(row["document_id"]) for row in rows if row.get("document_id")]
    logger.debug(
        "Vector match company_id={} hits={}",
        company_id,
        len(ids),
    )
    return ids


async def run_aggregate(
    company_id: str,
    aggregation: str,
    filters: dict[str, Any],
    *,
    metric_field: str | None = None,
    scope_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Call intelligence_aggregate RPC — SQL uses GROUP BY / aggregates only."""
    client = await get_supabase_client()
    scope_uuid: list[str] | None = None
    if scope_ids:
        scope_uuid = [str(UUID(i)) for i in scope_ids]

    payload: dict[str, Any] = {
        "p_company_id": company_id,
        "p_aggregation": aggregation,
        "p_filters": filters,
        "p_metric_field": metric_field or "ltv_usd",
        "p_scope_ids": scope_uuid,
    }
    response = await client.rpc("intelligence_aggregate", payload).execute()
    data = response.data
    if isinstance(data, list):
        if not data:
            return {}
        data = data[0]
    return dict(data) if data else {}
