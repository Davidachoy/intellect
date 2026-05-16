"""POST /query — natural language intelligence queries."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from agents.run import run_query
from fastapi import APIRouter, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field

from db.client import get_supabase_client
from dependencies import AuthenticatedCompanyDep
from middleware.auth import hash_api_key
from shared.models.query import QueryRequest, QueryResponse

router = APIRouter(tags=["queries"])

DEFAULT_TARGET_COMPANY_ID = UUID("a0000000-0000-4000-8000-000000000001")


class QueryMeta(BaseModel):
    query_id: str
    cost: float = Field(..., ge=0)
    blocked: bool


class QueryEnvelope(BaseModel):
    data: QueryResponse
    meta: QueryMeta


def _state_to_response(state: dict[str, Any]) -> QueryResponse:
    blocked = not state.get("passed_privacy", True)
    return QueryResponse(
        query_id=state["query_id"],
        response=state.get("response") or state.get("sanitized_response") or "",
        blocked=blocked,
        block_reason=state.get("block_reason"),
        cost_usd=float(state.get("cost_usd") or 0.0),
        sensitivity_tier=str(state.get("sensitivity_tier") or "sensitive"),
    )


def _max_record_count(state: dict[str, Any]) -> int | None:
    counts = state.get("record_counts") or []
    if not counts:
        return None
    return max(counts)


async def _persist_query(
    *,
    query_id: str,
    api_key_hash: str,
    target_company_id: str,
    raw_query: str,
    state: dict[str, Any],
) -> None:
    blocked = not state.get("passed_privacy", True)
    row = {
        "id": query_id,
        "querier_api_key_hash": api_key_hash,
        "target_company_id": target_company_id,
        "raw_query": raw_query,
        "structured_query": state.get("structured_query"),
        "response": state.get("response") or state.get("sanitized_response"),
        "blocked": blocked,
        "block_reason": state.get("block_reason"),
        "cost_usd": state.get("cost_usd") or 0.0,
        "record_count": _max_record_count(state),
    }
    client = await get_supabase_client()
    await client.table("queries").insert(row).execute()


async def _persist_audit_trail(query_id: str, state: dict[str, Any]) -> None:
    blocked = not state.get("passed_privacy", True)
    steps: list[tuple[str, str, dict[str, Any]]] = [
        (
            "query_router",
            "routed",
            {
                "structured_query": state.get("structured_query"),
                "target_agent_ids": state.get("target_agent_ids"),
            },
        ),
        (
            "intelligence",
            "aggregated",
            {
                "record_counts": state.get("record_counts"),
                "insight_count": len(state.get("raw_insights") or []),
            },
        ),
        (
            "privacy_guard",
            "blocked" if blocked else "approved",
            {
                "passed_privacy": state.get("passed_privacy"),
                "block_reason": state.get("block_reason"),
            },
        ),
    ]
    if not blocked:
        steps.append(
            (
                "pricing",
                "charged",
                {
                    "cost_usd": state.get("cost_usd"),
                    "sensitivity_tier": state.get("sensitivity_tier"),
                },
            )
        )

    client = await get_supabase_client()
    rows = [
        {
            "query_id": query_id,
            "agent": agent,
            "event": event,
            "payload": payload,
        }
        for agent, event, payload in steps
    ]
    await client.table("audit_log").insert(rows).execute()


@router.post("/query", response_model=QueryEnvelope)
async def submit_query(
    body: QueryRequest,
    company: AuthenticatedCompanyDep,
) -> QueryEnvelope:
    query_id = str(uuid4())
    target_company_id = str(DEFAULT_TARGET_COMPANY_ID)
    api_key_hash = hash_api_key(body.querier_api_key)

    try:
        state = await run_query(
            body.raw_query,
            target_company_id,
            query_id=query_id,
            querier_company_id=str(company.company_id),
        )
    except Exception as exc:
        logger.exception("run_query failed for query_id={}", query_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Query processing failed",
        ) from exc

    if state.get("error"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=state["error"],
        )

    try:
        await _persist_query(
            query_id=query_id,
            api_key_hash=api_key_hash,
            target_company_id=target_company_id,
            raw_query=body.raw_query,
            state=state,
        )
        await _persist_audit_trail(query_id, state)
    except RuntimeError as exc:
        logger.exception("Database unavailable for query_id={}", query_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Audit persistence unavailable",
        ) from exc
    except Exception as exc:
        logger.exception("Failed to persist query audit for query_id={}", query_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist query audit trail",
        ) from exc

    data = _state_to_response(state)
    return QueryEnvelope(
        data=data,
        meta=QueryMeta(
            query_id=data.query_id,
            cost=data.cost_usd,
            blocked=data.blocked,
        ),
    )
