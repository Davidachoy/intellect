from loguru import logger

from model_registry import log_configured_node
from query_router.router import route_query_with_attribution
from state import QueryState


async def query_router_node(state: QueryState) -> dict[str, object]:
    """LangGraph node: NL query → structured_query + target_agent_ids."""
    raw_query = state.get("raw_query", "").strip()
    attribution_map = dict(state.get("model_attribution") or {})
    log_configured_node("intelligence")

    if not raw_query:
        logger.warning("query_router_node: missing raw_query")
        return {
            "structured_query": {},
            "target_agent_ids": [],
            "error": "Missing raw_query",
            "model_attribution": attribution_map,
        }

    try:
        routed = await route_query_with_attribution(raw_query)
    except Exception as exc:
        logger.exception("Query router failed")
        return {
            "structured_query": {},
            "target_agent_ids": [],
            "error": f"Router error: {exc}",
            "model_attribution": attribution_map,
        }

    attribution_map["router"] = routed.attribution.model_dump()
    return {
        "structured_query": routed.result.structured_query.model_dump(),
        "target_agent_ids": routed.result.target_agent_ids,
        "error": None,
        "model_attribution": attribution_map,
    }
