from loguru import logger

from state import QueryState


async def privacy_guard_node(state: QueryState) -> QueryState:
    logger.info(
        "privacy_guard: stub pass-through",
        query_id=state["query_id"],
        passed_privacy=state["passed_privacy"],
    )
    return state
