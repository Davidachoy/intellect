"""LangGraph topology for API and web visualization (mirrors packages/agents/graph.py)."""

from __future__ import annotations

from typing import Literal

GraphNodeId = Literal[
    "query_router",
    "benchmark",
    "intelligence",
    "explainer",
    "synthesis",
    "pricing",
    "privacy_guard",
    "end",
]

GRAPH_NODES: tuple[dict[str, str], ...] = (
    {"id": "query_router", "label": "Query Router"},
    {"id": "benchmark", "label": "Benchmark"},
    {"id": "intelligence", "label": "Intelligence"},
    {"id": "explainer", "label": "Query Explainer"},
    {"id": "synthesis", "label": "Synthesis"},
    {"id": "pricing", "label": "Pricing"},
    {"id": "privacy_guard", "label": "Privacy Guard"},
    {"id": "end", "label": "END"},
)

GRAPH_EDGES: tuple[dict[str, str], ...] = (
    {"id": "e-router-bench", "source": "query_router", "target": "benchmark", "label": "benchmark"},
    {"id": "e-router-intel", "source": "query_router", "target": "intelligence"},
    {"id": "e-bench-explainer", "source": "benchmark", "target": "explainer"},
    {"id": "e-intel-explainer", "source": "intelligence", "target": "explainer"},
    {"id": "e-explainer-pricing", "source": "explainer", "target": "pricing"},
    {"id": "e-pricing-privacy", "source": "pricing", "target": "privacy_guard"},
    {"id": "e-privacy-end-ok", "source": "privacy_guard", "target": "end", "label": "complete"},
    {"id": "e-privacy-end-block", "source": "privacy_guard", "target": "end", "label": "blocked"},
)

PIPELINE_NODE_ORDER: tuple[str, ...] = (
    "query_router",
    "benchmark",
    "intelligence",
    "explainer",
    "pricing",
    "privacy_guard",
)
