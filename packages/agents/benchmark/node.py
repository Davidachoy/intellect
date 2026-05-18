"""Benchmark LangGraph node — sector-wide metrics when intent is benchmark."""

from __future__ import annotations

from benchmark.aggregator import aggregate_sector_benchmark
from loguru import logger
from model_registry import attribution_for_configured_node, log_attribution
from state import QueryState


async def benchmark_node(state: QueryState) -> dict[str, object]:
    entry = attribution_for_configured_node("intelligence")
    log_attribution(entry)
    attribution_map = dict(state.get("model_attribution") or {})
    attribution_map["benchmark"] = entry.model_dump()

    if state.get("error"):
        logger.warning("benchmark: skipping due to upstream error query_id={}", state["query_id"])
        return {
            "raw_insights": [],
            "record_counts": [],
            "model_attribution": attribution_map,
        }

    structured = state.get("structured_query") or {}
    result = await aggregate_sector_benchmark(
        structured,
        raw_query=state.get("raw_query", ""),
        target_company_id=state.get("target_company_id") or None,
        mentioned_companies=(structured.get("mentioned_companies") or None),
    )

    logger.info(
        "benchmark: query_id={} companies_in_sector={}",
        state["query_id"],
        (result.get("raw_insights") or [{}])[0].get("company_count", 0)
        if result.get("raw_insights")
        else 0,
    )

    updates: dict[str, object] = {
        "intelligence_results": [],
        "raw_insights": result.get("raw_insights") or [],
        "record_counts": result.get("record_counts") or [],
        "response": result.get("response") or "",
        "model_attribution": attribution_map,
    }
    if result.get("target_company_id"):
        updates["target_company_id"] = result["target_company_id"]
    return updates
