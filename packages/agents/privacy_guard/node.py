from loguru import logger

from privacy_guard.client import classify_reconstruction_with_featherless
from privacy_guard.guard import run_privacy_guard
from query_router.llm_parse import OUT_OF_SCOPE_INTENT
from shared.constants import OUT_OF_SCOPE_RESPONSE
from state import QueryState


def _block_updates(
    state: QueryState,
    attribution_map: dict[str, object],
    *,
    block_reason: str,
    attribution: dict[str, object] | None = None,
) -> dict[str, object]:
    if attribution is not None:
        attribution_map["privacy_guard"] = attribution
    return {
        "passed_privacy": False,
        "block_reason": block_reason,
        "sanitized_response": "",
        "response": "",
        "cost_usd": 0.0,
        "model_attribution": attribution_map,
    }


async def privacy_guard_node(state: QueryState) -> dict[str, object]:
    attribution_map = dict(state.get("model_attribution") or {})
    structured = state.get("structured_query") or {}

    # Reconstruction check always runs first (even when router marks out-of-scope).
    safe, recon_reason, recon_attribution = await classify_reconstruction_with_featherless(
        state["raw_query"]
    )
    if not safe:
        return _block_updates(
            state,
            attribution_map,
            block_reason=recon_reason
            or "Query appears designed to reconstruct individual records",
            attribution=recon_attribution.model_dump(),
        )

    upstream_error = state.get("error")
    if upstream_error:
        logger.warning(
            "privacy_guard: blocking due to upstream error query_id={}",
            state["query_id"],
        )
        return _block_updates(
            state,
            attribution_map,
            block_reason=f"Query processing failed: {upstream_error}",
        )

    if structured.get("intent") == OUT_OF_SCOPE_INTENT:
        from model_registry import attribution_for_configured_node

        guard_entry = attribution_for_configured_node("privacy_guard")
        attribution_map["privacy_guard"] = guard_entry.model_dump()
        logger.info(
            "privacy_guard: out-of-scope approved query_id={}",
            state["query_id"],
        )
        return {
            "passed_privacy": True,
            "block_reason": None,
            "sanitized_response": OUT_OF_SCOPE_RESPONSE,
            "response": OUT_OF_SCOPE_RESPONSE,
            "cost_usd": 0.0,
            "sensitivity_tier": "public",
            "model_attribution": attribution_map,
        }

    if not state.get("raw_insights") and not state.get("record_counts"):
        return _block_updates(
            state,
            attribution_map,
            block_reason="No aggregated insight available for this query",
            attribution=recon_attribution.model_dump(),
        )

    result, attribution = await run_privacy_guard(
        raw_query=state["raw_query"],
        record_counts=list(state.get("record_counts") or []),
        response=state.get("response") or "",
        sanitized_response=state.get("sanitized_response") or "",
        raw_insights=list(state.get("raw_insights") or []),
        skip_reconstruction=True,
    )

    attribution_map["privacy_guard"] = attribution.model_dump()

    updates: dict[str, object] = {
        "passed_privacy": result.passed,
        "block_reason": result.block_reason,
        "sanitized_response": result.sanitized_response,
        "record_counts": result.record_counts,
        "model_attribution": attribution_map,
    }

    if result.passed:
        updates["response"] = result.sanitized_response
    else:
        updates["response"] = ""
        updates["cost_usd"] = 0.0

    logger.info(
        "privacy_guard: query_id={} passed={} block_reason={}",
        state["query_id"],
        result.passed,
        result.block_reason,
    )
    return updates
