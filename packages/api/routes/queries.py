"""POST /query — natural language intelligence queries."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from agents.graph_events import node_audit_event, summarize_node_update
from agents.run import run_query
from fastapi import APIRouter, HTTPException, Response, status
from loguru import logger
from pydantic import BaseModel, Field

from db.client import get_supabase_client
from dependencies import AuthenticatedCompanyDep
from middleware.auth import hash_api_key
from shared.models.query import QueryRequest, QueryResponse

router = APIRouter(tags=["queries"])

DEFAULT_TARGET_COMPANY_ID = UUID("a0000000-0000-4000-8000-000000000001")


@router.options("/query")
async def query_preflight() -> Response:
    return Response(status_code=status.HTTP_200_OK)


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
        explanation=state.get("explanation") or None,
    )


def _max_record_count(state: dict[str, Any]) -> int | None:
    counts = state.get("record_counts") or []
    if not counts:
        return None
    return max(counts)


def _resolve_target_company_id(state: dict[str, Any], fallback: str) -> str:
    results = state.get("intelligence_results") or []
    if results:
        return str(results[0].get("company_id") or fallback)
    explicit = state.get("target_company_id")
    if explicit:
        return str(explicit)
    return fallback


async def _persist_audit_step(
    query_id: str,
    agent: str,
    event: str,
    payload: dict[str, Any],
) -> None:
    client = await get_supabase_client()
    await client.table("audit_log").insert(
        {
            "query_id": query_id,
            "agent": agent,
            "event": event,
            "payload": payload,
        }
    ).execute()


async def _ensure_query_row(
    *,
    query_id: str,
    api_key_hash: str,
    target_company_id: str,
    raw_query: str,
) -> None:
    """Insert placeholder query row so incremental audit_log FK inserts succeed."""
    client = await get_supabase_client()
    row = {
        "id": query_id,
        "querier_api_key_hash": api_key_hash,
        "target_company_id": target_company_id,
        "raw_query": raw_query,
        "structured_query": None,
        "response": None,
        "blocked": False,
        "block_reason": None,
        "cost_usd": 0.0,
        "record_count": None,
    }
    await client.table("queries").upsert(row, on_conflict="id").execute()


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
    await client.table("queries").upsert(row, on_conflict="id").execute()


async def _persist_audit_from_state(query_id: str, state: dict[str, Any]) -> None:
    """Persist full audit trail (used when incremental writes were skipped)."""
    blocked = not state.get("passed_privacy", True)
    steps: list[tuple[str, str, dict[str, Any]]] = [
        (
            "query_router",
            "routed",
            summarize_node_update("query_router", state),
        ),
    ]

    intel_results = state.get("intelligence_results") or []
    steps.append(
        (
            "explainer",
            "explained",
            {
                "preview": (state.get("explanation") or "")[:200],
                "chars": len(state.get("explanation") or ""),
            },
        )
    )

    if intel_results:
        for result in intel_results:
            steps.append(
                (
                    "intelligence",
                    "aggregated",
                    {
                        "company_name": result.get("company_name"),
                        "agent_id": result.get("agent_id"),
                        "record_counts": result.get("record_counts"),
                        "insight_count": len(result.get("raw_insights") or []),
                        "error": result.get("error"),
                    },
                )
            )
        if len(intel_results) > 1:
            steps.append(
                (
                    "synthesis",
                    "merged",
                    {
                        "company_count": len(intel_results),
                        "preview": (state.get("response") or "")[:200],
                    },
                )
            )
    elif (state.get("structured_query") or {}).get("intent") == "benchmark":
        steps.append(
            (
                "benchmark",
                "aggregated",
                summarize_node_update("benchmark", state),
            )
        )
    else:
        steps.append(
            (
                "intelligence",
                "aggregated",
                summarize_node_update("intelligence", state),
            )
        )

    if state.get("explanation"):
        steps.append(
            (
                "explainer",
                "explained",
                summarize_node_update("explainer", state),
            )
        )

    steps.append(
        (
            "pricing",
            "charged" if not blocked else "skipped",
            summarize_node_update("pricing", state),
        )
    )
    steps.append(
        (
            "privacy_guard",
            "blocked" if blocked else "approved",
            summarize_node_update("privacy_guard", state),
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


async def _persist_node_audit(
    query_id: str,
    node: str,
    update: dict[str, Any],
) -> None:
    """Write audit rows for a single completed graph node."""
    if node == "benchmark":
        await _persist_audit_step(
            query_id,
            "benchmark",
            "aggregated",
            summarize_node_update("benchmark", update),
        )
        return

    if node == "intelligence":
        results = update.get("intelligence_results") or []
        if results:
            for result in results:
                await _persist_audit_step(
                    query_id,
                    "intelligence",
                    "aggregated",
                    {
                        "company_name": result.get("company_name"),
                        "agent_id": result.get("agent_id"),
                        "record_counts": result.get("record_counts"),
                        "insight_count": len(result.get("raw_insights") or []),
                        "error": result.get("error"),
                    },
                )
            if len(results) > 1:
                await _persist_audit_step(
                    query_id,
                    "synthesis",
                    "merged",
                    {
                        "company_count": len(results),
                        "preview": (update.get("response") or "")[:200],
                    },
                )
            return

    agent, event = node_audit_event(node, update)
    await _persist_audit_step(
        query_id,
        agent,
        event,
        summarize_node_update(node, update),
    )


async def _execute_query(
    *,
    query_id: str,
    raw_query: str,
    target_company_id: str | None,
    querier_company_id: str,
    api_key_hash: str,
    incremental_audit: bool,
) -> dict[str, Any]:
    target = str(target_company_id) if target_company_id else None

    async def on_node_event(node: str, event: str, update: dict[str, Any]) -> None:
        if not incremental_audit or event != "end":
            return
        try:
            await _persist_node_audit(query_id, node, update)
        except Exception:
            logger.exception(
                "Incremental audit failed query_id={} node={}",
                query_id,
                node,
            )

    state = await run_query(
        raw_query,
        target,
        query_id=query_id,
        querier_company_id=querier_company_id,
        on_node_event=on_node_event,
    )

    if state.get("error"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=state["error"],
        )

    resolved_target = _resolve_target_company_id(
        state,
        str(target_company_id or DEFAULT_TARGET_COMPANY_ID),
    )

    await _persist_query(
        query_id=query_id,
        api_key_hash=api_key_hash,
        target_company_id=resolved_target,
        raw_query=raw_query,
        state=state,
    )
    if not incremental_audit:
        await _persist_audit_from_state(query_id, state)

    return state


@router.post("/query", response_model=QueryEnvelope)
async def submit_query(
    body: QueryRequest,
    company: AuthenticatedCompanyDep,
) -> QueryEnvelope:
    query_id = str(uuid4())
    api_key_hash = hash_api_key(body.querier_api_key)

    try:
        state = await _execute_query(
            query_id=query_id,
            raw_query=body.raw_query,
            target_company_id=body.target_company_id,
            querier_company_id=str(company.company_id),
            api_key_hash=api_key_hash,
            incremental_audit=True,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("run_query failed for query_id={}", query_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Query processing failed",
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
