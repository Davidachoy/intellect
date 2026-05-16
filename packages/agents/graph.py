from typing import Literal

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from benchmark.node import benchmark_node
from explainer.node import explainer_node
from intelligence.node import intelligence_node
from pricing.node import pricing_node
from privacy_guard.node import privacy_guard_node
from query_router.node import query_router_node
from state import QueryState

RouteAfterPrivacy = Literal["complete", "blocked"]
RouteAfterRouter = Literal["benchmark", "intelligence"]


def _route_after_privacy(state: QueryState) -> RouteAfterPrivacy:
    if state.get("passed_privacy"):
        return "complete"
    return "blocked"


def _route_after_router(state: QueryState) -> RouteAfterRouter:
    intent = (state.get("structured_query") or {}).get("intent", "").strip().lower()
    if intent == "benchmark":
        return "benchmark"
    return "intelligence"


def build_graph() -> CompiledStateGraph:
    graph = StateGraph(QueryState)

    graph.add_node("query_router", query_router_node)
    graph.add_node("benchmark", benchmark_node)
    graph.add_node("intelligence", intelligence_node)
    graph.add_node("explainer", explainer_node)
    graph.add_node("pricing", pricing_node)
    graph.add_node("privacy_guard", privacy_guard_node)

    graph.set_entry_point("query_router")
    graph.add_conditional_edges(
        "query_router",
        _route_after_router,
        {
            "benchmark": "benchmark",
            "intelligence": "intelligence",
        },
    )
    graph.add_edge("benchmark", "explainer")
    graph.add_edge("intelligence", "explainer")
    graph.add_edge("explainer", "pricing")
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
