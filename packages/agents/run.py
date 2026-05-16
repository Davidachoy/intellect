"""Agent pipeline entry point."""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from loguru import logger

from graph import get_graph
from model_registry import gemini_nodes_summary
from state import QueryState, initial_state

DEFAULT_TARGET_COMPANY_ID = "a0000000-0000-4000-8000-000000000001"

GraphNodeCallback = Callable[[str, str, dict[str, Any]], Awaitable[None]]


def _merge_state(state: QueryState, update: dict[str, Any]) -> QueryState:
    merged = dict(state)
    merged.update(update)
    return merged  # type: ignore[return-value]


async def run_query(
    query: str,
    company_id: str | None = None,
    *,
    query_id: str | None = None,
    querier_company_id: str | None = None,
    on_node_event: GraphNodeCallback | None = None,
) -> QueryState:
    """Run the compiled LangGraph pipeline end-to-end with optional per-node callbacks."""
    qid = query_id or str(uuid.uuid4())
    target = company_id if company_id is not None else ""
    querier_id = querier_company_id or target or DEFAULT_TARGET_COMPANY_ID

    state = initial_state(
        raw_query=query,
        target_company_id=target,
        query_id=qid,
        querier_company_id=querier_id,
    )

    logger.info("run_query: streaming graph query_id={}", qid)
    accumulated: QueryState = state
    graph = get_graph()

    async for chunk in graph.astream(state, stream_mode="updates"):
        for node_name, update in chunk.items():
            logger.info(
                "pipeline trace query_id={} node={} keys={}",
                qid,
                node_name,
                sorted(update.keys()),
            )
            accumulated = _merge_state(accumulated, update)
            if on_node_event:
                await on_node_event(node_name, "end", dict(update))

    logger.info("pipeline trace query_id={} graph_complete", qid)
    return accumulated


async def run_graph(query: str, target_company_id: str) -> QueryState:
    """Alias for run_query without explicit query_id (CLI convenience)."""
    return await run_query(query, target_company_id)


def _print_attribution_summary(state: QueryState) -> None:
    print("\n--- Model attribution (hackathon demo) ---")
    attribution = state.get("model_attribution") or {}
    for node, entry in attribution.items():
        used = entry.get("used_gemini", False)
        model = entry.get("model") or entry.get("backend", "-")
        tracks = ", ".join(entry.get("hackathon_tracks") or []) or "none"
        gemini_flag = " [Gemini]" if used else ""
        print(f"  {node}: {model}{gemini_flag}  tracks=[{tracks}]")

    hackathon_mode = os.getenv("HACKATHON_GOOGLE_TRACK", "").lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    router = attribution.get("router") or {}
    if hackathon_mode and not router.get("used_gemini"):
        print(
            "\n  Router did not call Gemini. For the Google track demo, set in .env:\n"
            "    ROUTER_MODEL=gemini/gemini-2.0-flash\n"
            "  or HACKATHON_GOOGLE_TRACK=true (with GEMINI_API_KEY set)\n"
        )

    print("\nConfigured Gemini defaults:", gemini_nodes_summary())
    print()


async def _main() -> None:
    raw_query = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "how many active clients does this company have in Italy?"
    )
    target_company_id = (
        sys.argv[2] if len(sys.argv) > 2 else DEFAULT_TARGET_COMPANY_ID
    )

    state = await run_query(raw_query, target_company_id)

    _print_attribution_summary(state)
    blocked = not state.get("passed_privacy", True)
    print("blocked:", blocked)
    if blocked:
        print("block_reason:", state.get("block_reason"))
    elif state.get("error"):
        print("error:", state.get("error"))
    print("response:", state.get("response") or "")
    if state.get("cost_usd") is not None:
        print("cost_usd:", state.get("cost_usd"))


if __name__ == "__main__":
    asyncio.run(_main())
