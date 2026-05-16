from loguru import logger

from query_router.router import route_query
from state import QueryState


async def query_router_node(state: QueryState) -> dict[str, object]:
    """LangGraph node: NL query → structured_query + target_agent_ids."""
    raw_query = state.get("raw_query", "").strip()
    if not raw_query:
        logger.warning("query_router_node: missing raw_query")
        return {
            "structured_query": {},
            "target_agent_ids": [],
            "error": "Missing raw_query",
        }

    try:
        result = await route_query(raw_query)
    except Exception as exc:
        logger.exception("Query router failed")
        return {
            "structured_query": {},
            "target_agent_ids": [],
            "error": f"Router error: {exc}",
        }

    return {
        "structured_query": result.structured_query.model_dump(),
        "target_agent_ids": result.target_agent_ids,
        "error": None,
    }
