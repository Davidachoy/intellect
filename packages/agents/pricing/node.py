from loguru import logger

from state import QueryState


async def pricing_node(state: QueryState) -> QueryState:
    logger.info(
        "pricing: stub pass-through",
        query_id=state["query_id"],
        sensitivity_tier=state["sensitivity_tier"],
    )
    return state
