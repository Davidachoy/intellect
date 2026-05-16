from typing import TypedDict
from uuid import uuid4


class QueryState(TypedDict):
    # Input
    query_id: str
    raw_query: str
    querier_company_id: str
    target_company_id: str

    # Router output
    structured_query: dict
    target_agent_ids: list[str]

    # Intelligence Agent output
    raw_insights: list[dict]
    record_counts: list[int]

    # Privacy Guard output
    passed_privacy: bool
    block_reason: str | None
    sanitized_response: str

    # Pricing output
    cost_usd: float
    sensitivity_tier: str

    # Final
    response: str
    error: str | None


def initial_state(
    raw_query: str,
    target_company_id: str,
    *,
    query_id: str | None = None,
    querier_company_id: str = "",
) -> QueryState:
    return QueryState(
        query_id=query_id or str(uuid4()),
        raw_query=raw_query,
        querier_company_id=querier_company_id,
        target_company_id=target_company_id,
        structured_query={},
        target_agent_ids=[],
        raw_insights=[],
        record_counts=[],
        passed_privacy=True,
        block_reason=None,
        sanitized_response="",
        cost_usd=0.0,
        sensitivity_tier="aggregated",
        response="",
        error=None,
    )
