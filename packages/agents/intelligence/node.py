import asyncio

from loguru import logger

from intelligence.base import IntelligenceAgent
from intelligence.plans import build_intelligence_jobs
from intelligence.synthesize import synthesize_multi_company_response
from model_registry import attribution_for_configured_node, log_attribution
from privacy_guard.checks import check_reconstruction
from query_router.llm_parse import OUT_OF_SCOPE_INTENT
from state import QueryState

_UNSUPPORTED_AGGREGATIONS = frozenset({"none", ""})


async def _run_job(job: object) -> dict[str, object]:
    from intelligence.plans import IntelligenceJob

    assert isinstance(job, IntelligenceJob)
    try:
        result = await IntelligenceAgent(job.company_id, job.structured_query).run()
        return {
            "agent_id": job.agent_id,
            "company_id": job.company_id,
            "company_name": job.company_name,
            "structured_query": job.structured_query,
            "raw_insights": result.raw_insights,
            "record_counts": result.record_counts,
            "error": None,
        }
    except Exception as exc:
        logger.exception(
            "intelligence: RAG failed company={} query_id branch",
            job.company_name,
        )
        return {
            "agent_id": job.agent_id,
            "company_id": job.company_id,
            "company_name": job.company_name,
            "structured_query": job.structured_query,
            "raw_insights": [],
            "record_counts": [],
            "error": str(exc),
        }


async def intelligence_node(state: QueryState) -> dict[str, object]:
    entry = attribution_for_configured_node("intelligence")
    log_attribution(entry)
    attribution_map = dict(state.get("model_attribution") or {})
    attribution_map["intelligence"] = entry.model_dump()

    empty = {
        "intelligence_results": [],
        "raw_insights": [],
        "record_counts": [],
        "model_attribution": attribution_map,
    }

    if state.get("error"):
        logger.warning(
            "intelligence: skipping RAG due to upstream error query_id={}",
            state["query_id"],
        )
        return empty

    raw_query = state.get("raw_query", "")
    if not check_reconstruction(raw_query):
        logger.info(
            "intelligence: skipping RAG for reconstruction-shaped query query_id={}",
            state["query_id"],
        )
        return empty

    structured = state.get("structured_query") or {}
    aggregation = (structured.get("aggregation") or "").strip().lower()
    if aggregation in _UNSUPPORTED_AGGREGATIONS:
        logger.info(
            "intelligence: skipping RAG for non-aggregate intent={} aggregation={}",
            structured.get("intent"),
            aggregation,
        )
        return empty

    if structured.get("intent") == OUT_OF_SCOPE_INTENT:
        logger.info(
            "intelligence: out-of-scope query_id={}",
            state["query_id"],
        )
        return empty

    jobs = build_intelligence_jobs(
        structured_query=structured,
        target_agent_ids=list(state.get("target_agent_ids") or []),
        target_company_id=state.get("target_company_id") or "",
        raw_query=raw_query,
    )
    logger.info(
        "intelligence trace query_id={} jobs={}",
        state["query_id"],
        [(j.company_name, j.structured_query.get("domain")) for j in jobs],
    )

    results = await asyncio.gather(*[_run_job(job) for job in jobs])

    merged_insights: list[dict] = []
    merged_counts: list[int] = []
    errors: list[str] = []

    for result in results:
        for insight in result.get("raw_insights") or []:
            tagged = dict(insight)
            tagged.setdefault("company_name", result.get("company_name"))
            merged_insights.append(tagged)
        merged_counts.extend(result.get("record_counts") or [])
        if result.get("error"):
            errors.append(str(result["error"]))

    synthesized = synthesize_multi_company_response(results)

    logger.info(
        "intelligence: aggregated query_id={} companies={} record_counts={}",
        state["query_id"],
        len(results),
        merged_counts,
    )

    updates: dict[str, object] = {
        "intelligence_results": results,
        "raw_insights": merged_insights,
        "record_counts": merged_counts,
        "response": synthesized,
        "model_attribution": attribution_map,
    }
    if errors and not merged_insights:
        updates["error"] = "; ".join(errors)
    return updates
