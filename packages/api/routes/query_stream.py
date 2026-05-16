"""POST /query/stream — Server-Sent Events for live LangGraph progress."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from uuid import uuid4

from agents.graph_events import NODE_ORDER
from agents.run import run_query
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from loguru import logger

from dependencies import AuthenticatedCompanyDep
from middleware.auth import hash_api_key
from routes.queries import (
    DEFAULT_TARGET_COMPANY_ID,
    QueryEnvelope,
    QueryMeta,
    _ensure_query_row,
    _persist_node_audit,
    _persist_query,
    _resolve_target_company_id,
    _state_to_response,
)
from shared.models.query import QueryRequest

router = APIRouter(tags=["queries"])


def _sse(event_type: str, payload: dict[str, Any]) -> str:
    body = json.dumps({"type": event_type, **payload})
    return f"data: {body}\n\n"


@router.post("/query/stream")
async def submit_query_stream(
    body: QueryRequest,
    company: AuthenticatedCompanyDep,
) -> StreamingResponse:
    query_id = str(uuid4())
    api_key_hash = hash_api_key(body.querier_api_key)
    target = str(body.target_company_id) if body.target_company_id else None

    async def event_generator():
        queue: asyncio.Queue[str | None] = asyncio.Queue()
        placeholder_target = str(
            body.target_company_id or DEFAULT_TARGET_COMPANY_ID
        )
        try:
            await _ensure_query_row(
                query_id=query_id,
                api_key_hash=api_key_hash,
                target_company_id=placeholder_target,
                raw_query=body.raw_query,
            )
        except Exception:
            logger.exception(
                "SSE query placeholder insert failed query_id={}", query_id
            )

        async def on_node_event(node: str, event: str, update: dict[str, Any]) -> None:
            if event != "end":
                return
            next_node: str | None = None
            if node == "query_router":
                intent = (
                    (update.get("structured_query") or {}).get("intent") or ""
                ).strip().lower()
                next_node = (
                    "benchmark" if intent == "benchmark" else "intelligence"
                )
            elif node in NODE_ORDER:
                idx = NODE_ORDER.index(node)
                if idx + 1 < len(NODE_ORDER):
                    next_node = NODE_ORDER[idx + 1]
            logger.info(
                "SSE trace query_id={} node_end node={} next={}",
                query_id,
                node,
                next_node,
            )
            await queue.put(
                _sse(
                    "node_end",
                    {
                        "query_id": query_id,
                        "node": node,
                        "update": update,
                    },
                )
            )
            if next_node:
                logger.info(
                    "SSE trace query_id={} node_start node={}",
                    query_id,
                    next_node,
                )
                await queue.put(
                    _sse("node_start", {"query_id": query_id, "node": next_node})
                )
            try:
                await _persist_node_audit(query_id, node, update)
            except Exception:
                logger.exception("SSE audit persist failed node={}", node)

        async def run_pipeline() -> None:
            try:
                state = await run_query(
                    body.raw_query,
                    target,
                    query_id=query_id,
                    querier_company_id=str(company.company_id),
                    on_node_event=on_node_event,
                )
            except Exception as exc:
                logger.exception("stream run_query failed query_id={}", query_id)
                await queue.put(
                    _sse("error", {"query_id": query_id, "message": str(exc)})
                )
                await queue.put(None)
                return

            if state.get("error"):
                await queue.put(
                    _sse(
                        "error",
                        {"query_id": query_id, "message": state["error"]},
                    )
                )
                await queue.put(None)
                return

            resolved_target = _resolve_target_company_id(
                state,
                str(body.target_company_id or DEFAULT_TARGET_COMPANY_ID),
            )
            try:
                await _persist_query(
                    query_id=query_id,
                    api_key_hash=api_key_hash,
                    target_company_id=resolved_target,
                    raw_query=body.raw_query,
                    state=state,
                )
            except Exception:
                logger.exception("SSE query persist failed query_id={}", query_id)

            data = _state_to_response(state)
            envelope = QueryEnvelope(
                data=data,
                meta=QueryMeta(
                    query_id=data.query_id,
                    cost=data.cost_usd,
                    blocked=data.blocked,
                ),
            )
            logger.info("SSE trace query_id={} stream_complete", query_id)
            await queue.put(
                _sse(
                    "complete",
                    {
                        "query_id": query_id,
                        "envelope": envelope.model_dump(),
                    },
                )
            )
            await queue.put(None)

        logger.info("SSE trace query_id={} stream_open", query_id)
        yield _sse(
            "query_started",
            {"query_id": query_id, "nodes": list(NODE_ORDER)},
        )
        logger.info("SSE trace query_id={} node_start node=query_router", query_id)
        yield _sse("node_start", {"query_id": query_id, "node": "query_router"})

        task = asyncio.create_task(run_pipeline())
        while True:
            message = await queue.get()
            if message is None:
                break
            yield message
        await task

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
