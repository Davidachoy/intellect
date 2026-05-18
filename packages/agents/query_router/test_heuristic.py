"""Heuristic router tests — no Gemini, no mocks."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

_AGENTS_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _AGENTS_ROOT.parents[1]
for path in (
    str(_REPO_ROOT / "packages" / "shared"),
    str(_REPO_ROOT / "packages"),
    str(_AGENTS_ROOT),
):
    if path not in sys.path:
        sys.path.insert(0, path)

from query_router.heuristic import generate_heuristic_router_output
from query_router.router import route_query

ACME_AGENT = "b1000000-0000-4000-8000-000000000001"
NORD_AGENT = "b1000000-0000-4000-8000-000000000002"
MED_AGENT = "b1000000-0000-4000-8000-000000000003"


@pytest.mark.parametrize(
    ("raw_query", "intent", "domain", "filters", "agent_ids"),
    [
        (
            "how many active clients does this company have in Italy?",
            "count",
            "customers",
            {"region": "Italy", "status": "active"},
            [ACME_AGENT],
        ),
        (
            "What is the average LTV for premium segment customers?",
            "average",
            "retail_customers",
            {"segment": "premium"},
            [ACME_AGENT],
        ),
        (
            "How many delayed shipments does NordLogistics have in Germany?",
            "count",
            "logistics_shipments",
            {"region": "Germany", "status": "delayed"},
            [NORD_AGENT],
        ),
        (
            "What percentage of trial participants had positive outcomes?",
            "percentage",
            "clinical_trials",
            {"outcome": "positive"},
            [MED_AGENT],
        ),
    ],
)
def test_heuristic_single_queries(
    raw_query: str,
    intent: str,
    domain: str,
    filters: dict[str, str],
    agent_ids: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ROUTER_MODE", "heuristic")
    output = asyncio.run(generate_heuristic_router_output(raw_query))
    assert output.intent == intent
    assert output.domain == domain
    assert output.filters == filters
    assert output.complexity == "simple"

    result = asyncio.run(route_query(raw_query))  # noqa: uses ROUTER_MODE=heuristic
    assert result.structured_query.intent == intent
    assert result.target_agent_ids == agent_ids


def test_heuristic_compound_query(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ROUTER_MODE", "heuristic")
    raw = (
        "How many Italian clients does Acme have and what is NordLogistics "
        "average shipment value?"
    )
    output = asyncio.run(generate_heuristic_router_output(raw))
    assert output.complexity == "compound"
    assert len(output.sub_queries) == 2
    assert output.sub_queries[0].domain == "customers"
    assert output.sub_queries[0].filters.get("region") == "Italy"
    assert output.sub_queries[1].domain == "logistics_shipments"
    assert output.sub_queries[1].intent == "average"

    result = asyncio.run(route_query(raw))
    assert ACME_AGENT in result.target_agent_ids
    assert NORD_AGENT in result.target_agent_ids


@pytest.mark.asyncio
async def test_heuristic_benchmark_intent_italy_sector() -> None:
    from query_router.heuristic import generate_heuristic_router_output

    output = await generate_heuristic_router_output(
        "How does Acme Retail compare to the sector in Italy?"
    )
    assert output.intent == "benchmark"
    assert output.filters.get("region") == "Italy"
    assert "Acme Retail" in output.mentioned_companies


def test_heuristic_compare_with_split(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ROUTER_MODE", "heuristic")
    raw = (
        "Compare active clients for Acme Retail in Italy with on-time shipment "
        "volume for NordLogistics in Italy."
    )
    output = asyncio.run(generate_heuristic_router_output(raw))
    assert output.complexity == "compound"
    assert output.intent == "compare"
    assert len(output.sub_queries) == 2

    result = asyncio.run(route_query(raw))
    assert ACME_AGENT in result.target_agent_ids
    assert NORD_AGENT in result.target_agent_ids
