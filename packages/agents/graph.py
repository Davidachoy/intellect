from typing import Literal

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from intelligence.node import intelligence_node
from pricing.node import pricing_node
from privacy_guard.node import privacy_guard_node
from query_router.node import query_router_node
from state import QueryState

RouteAfterPrivacy = Literal["complete", "blocked"]


def _route_after_privacy(state: QueryState) -> RouteAfterPrivacy:
    if state["passed_privacy"]:
        return "complete"
    return "blocked"


def build_graph() -> CompiledStateGraph:
    graph = StateGraph(QueryState)

    graph.add_node("router", query_router_node)
    graph.add_node("intelligence", intelligence_node)
    graph.add_node("pricing", pricing_node)
    graph.add_node("privacy_guard", privacy_guard_node)

    graph.set_entry_point("router")
    graph.add_edge("router", "intelligence")
    graph.add_edge("intelligence", "pricing")
    graph.add_edge("pricing", "privacy_guard")
    graph.add_conditional_edges(
        "privacy_guard",
        _route_after_privacy,
        {
            "complete": END,
            "blocked": END,
        },
    )

    return graph.compile()


_compiled_graph: CompiledStateGraph | None = None


def get_graph() -> CompiledStateGraph:
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph
