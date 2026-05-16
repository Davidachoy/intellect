from loguru import logger

from state import QueryState


async def intelligence_node(state: QueryState) -> QueryState:
    logger.info(
        "intelligence: stub pass-through",
        query_id=state["query_id"],
        target_company_id=state["target_company_id"],
    )
    return state
