from .tiers import TIERS, calculate_cost, cost_for_tier, resolve_sensitivity_tier

__all__ = [
    "TIERS",
    "calculate_cost",
    "cost_for_tier",
    "resolve_sensitivity_tier",
]


def __getattr__(name: str) -> object:
    if name == "pricing_node":
        from .node import pricing_node

        return pricing_node
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
