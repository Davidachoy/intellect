from loguru import logger

from pricing.tiers import calculate_cost, resolve_sensitivity_tier
from state import QueryState


async def pricing_node(state: QueryState) -> dict[str, object]:
    """Compute tier and cost; persistence is handled by the API layer."""
    structured = state.get("structured_query") or {}
    tier = resolve_sensitivity_tier(structured)
    cost = calculate_cost(tier, structured)

    logger.info(
        "pricing: charged query_id={} tier={} cost_usd={}",
        state["query_id"],
        tier,
        cost,
    )
    return {"cost_usd": cost, "sensitivity_tier": tier}
