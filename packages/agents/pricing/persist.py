"""Persist pricing transactions to Supabase queries + audit_log."""

from __future__ import annotations

import hashlib
import os
from typing import Any, Optional

from loguru import logger
from supabase import AsyncClient, acreate_client

from state import QueryState

_client: Optional[AsyncClient] = None


async def get_supabase_client() -> AsyncClient:
    global _client
    if _client is not None:
        return _client

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in the environment"
        )

    _client = await acreate_client(url, key)
    return _client


def _querier_api_key_hash(state: QueryState) -> str:
    """Stable hash for graph runs when only company id is available."""
    material = state.get("querier_company_id") or state.get("query_id", "")
    return hashlib.sha256(material.encode()).hexdigest()


def _max_record_count(state: QueryState) -> int | None:
    counts = state.get("record_counts") or []
    if not counts:
        return None
    return max(counts)


async def log_pricing_transaction(
    state: QueryState,
    *,
    cost_usd: float,
    sensitivity_tier: str,
) -> None:
    """Upsert query row with cost and append pricing audit entry."""
    try:
        client = await get_supabase_client()
    except RuntimeError:
        logger.warning(
            "pricing: Supabase not configured, skipping DB log query_id={}",
            state["query_id"],
        )
        return

    query_id = state["query_id"]
    row: dict[str, Any] = {
        "id": query_id,
        "querier_api_key_hash": _querier_api_key_hash(state),
        "target_company_id": state["target_company_id"],
        "raw_query": state["raw_query"],
        "structured_query": state.get("structured_query"),
        "cost_usd": cost_usd,
        "record_count": _max_record_count(state),
    }

    await client.table("queries").upsert(row, on_conflict="id").execute()
    await client.table("audit_log").insert(
        {
            "query_id": query_id,
            "agent": "pricing",
            "event": "charged",
            "payload": {
                "cost_usd": cost_usd,
                "sensitivity_tier": sensitivity_tier,
            },
        }
    ).execute()

    logger.debug(
        "pricing: persisted cost_usd={} tier={} query_id={}",
        cost_usd,
        sensitivity_tier,
        query_id,
    )
