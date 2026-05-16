"""Agent pipeline entry point — stub until LangGraph graph (TASK-004)."""

from __future__ import annotations

import re
import uuid

from agents.state import QueryState

DEFAULT_TARGET_COMPANY_ID = "a0000000-0000-4000-8000-000000000001"


def _is_reconstruction_query(query: str) -> bool:
    lowered = query.lower()
    patterns = (
        r"\blist\s+all\b",
        r"\bone\s+by\s+one\b",
        r"\beach\s+customer\b",
        r"\bindividual\s+records?\b",
    )
    return any(re.search(p, lowered) for p in patterns)


async def run_query(
    query: str,
    company_id: str,
    *,
    query_id: str | None = None,
    querier_company_id: str | None = None,
) -> QueryState:
    """Run the query pipeline and return final graph state."""
    qid = query_id or str(uuid.uuid4())
    querier_id = querier_company_id or company_id

    structured_query = {
        "intent": "count",
        "filters": {"region": "Italy", "status": "active"},
        "aggregation": "count",
        "domain": "customers",
    }
    record_counts = [847]
    raw_insights = [
        {
            "metric": "active_clients",
            "region": "Italy",
            "value": 847,
            "yoy_growth_pct": 23,
        }
    ]

    if _is_reconstruction_query(query):
        return QueryState(
            query_id=qid,
            raw_query=query,
            querier_company_id=querier_id,
            structured_query=structured_query,
            target_agent_ids=["b1000000-0000-4000-8000-000000000001"],
            raw_insights=raw_insights,
            record_counts=record_counts,
            passed_privacy=False,
            block_reason="Query appears designed to reconstruct individual records",
            sanitized_response="",
            cost_usd=0.0,
            sensitivity_tier="sensitive",
            response="",
            error=None,
        )

    return QueryState(
        query_id=qid,
        raw_query=query,
        querier_company_id=querier_id,
        structured_query=structured_query,
        target_agent_ids=["b1000000-0000-4000-8000-000000000001"],
        raw_insights=raw_insights,
        record_counts=record_counts,
        passed_privacy=True,
        block_reason=None,
        sanitized_response="847 active clients in Italy, 23% YoY growth",
        cost_usd=0.05,
        sensitivity_tier="sensitive",
        response="847 active clients in Italy, 23% YoY growth",
        error=None,
    )
