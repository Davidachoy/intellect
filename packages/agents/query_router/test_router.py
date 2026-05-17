"""Unit tests for Query Router — Gemini calls are mocked."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

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

from model_registry import attribution_from_invocation
from query_router.generation import RouterGenerationResult
from query_router.models import LLMRouterOutput, LLMSubQuery
from query_router.registry import resolve_agent_ids
from query_router.router import route_query
from shared.models.routing import StructuredQuery

ACME_AGENT = "b1000000-0000-4000-8000-000000000001"
NORD_AGENT = "b1000000-0000-4000-8000-000000000002"
MED_AGENT = "b1000000-0000-4000-8000-000000000003"


@pytest.mark.parametrize(
    ("domain", "raw_query", "expected_ids"),
    [
        ("customers", "how many clients in Italy?", [ACME_AGENT]),
        ("retail_customers", "Acme Retail segment breakdown", [ACME_AGENT]),
        ("logistics_shipments", "average shipment value in Nordics", [NORD_AGENT]),
        ("clinical_trials", "trial outcome percentage by region", [MED_AGENT]),
        (
            "shipments",
            "Compare NordLogistics delays vs MedResearch enrollment",
            [NORD_AGENT, MED_AGENT],
        ),
    ],
)
def test_resolve_agent_ids(
    domain: str,
    raw_query: str,
    expected_ids: list[str],
) -> None:
    ids = resolve_agent_ids(domain=domain, raw_query=raw_query)
    assert ids == expected_ids


def _mock_generation(llm_output: LLMRouterOutput) -> RouterGenerationResult:
    return RouterGenerationResult(
        output=llm_output,
        attribution=attribution_from_invocation(
            "router", model="gemini-3-flash-preview", backend="google-genai"
        ),
    )


@pytest.mark.parametrize(
    ("raw_query", "llm_output"),
    [
        (
            "how many active clients does this company have in Italy?",
            LLMRouterOutput(
                intent="count",
                filters={"region": "Italy", "status": "active"},
                aggregation="count",
                domain="customers",
            ),
        ),
        (
            "What is the average LTV for premium segment customers?",
            LLMRouterOutput(
                intent="average",
                filters={"segment": "premium"},
                aggregation="average",
                domain="retail_customers",
            ),
        ),
        (
            "How many delayed shipments does NordLogistics have in Germany?",
            LLMRouterOutput(
                intent="count",
                filters={"region": "Germany", "status": "delayed"},
                aggregation="count",
                domain="logistics_shipments",
                mentioned_companies=["NordLogistics"],
            ),
        ),
        (
            "What percentage of trial participants had positive outcomes?",
            LLMRouterOutput(
                intent="percentage",
                filters={"outcome": "positive"},
                aggregation="percentage",
                domain="clinical_trials",
            ),
        ),
        (
            "How many Italian clients does Acme have and what is NordLogistics average shipment value?",
            LLMRouterOutput(
                intent="count",
                filters={},
                aggregation="count",
                domain="customers",
                complexity="compound",
                sub_queries=[
                    LLMSubQuery(
                        intent="count",
                        filters={"region": "Italy"},
                        aggregation="count",
                        domain="customers",
                    ),
                    LLMSubQuery(
                        intent="average",
                        filters={},
                        aggregation="average",
                        domain="logistics_shipments",
                    ),
                ],
            ),
        ),
    ],
)
def test_route_query_mocked(raw_query: str, llm_output: LLMRouterOutput) -> None:
    with patch(
        "query_router.router.generate_router_output",
        new_callable=AsyncMock,
        return_value=_mock_generation(llm_output),
    ):
        result = asyncio.run(route_query(raw_query))

    assert isinstance(result.structured_query, StructuredQuery)
    assert result.structured_query.intent == llm_output.intent
    assert result.structured_query.aggregation == llm_output.aggregation
    assert result.structured_query.domain == llm_output.domain
    assert len(result.target_agent_ids) >= 1

    if llm_output.complexity == "compound":
        assert len(result.structured_query.sub_queries) == len(llm_output.sub_queries)


def test_route_query_italy_clients_example() -> None:
    llm_output = LLMRouterOutput(
        intent="count",
        filters={"region": "Italy", "status": "active"},
        aggregation="count",
        domain="customers",
    )
    with patch(
        "query_router.router.generate_router_output",
        new_callable=AsyncMock,
        return_value=_mock_generation(llm_output),
    ):
        result = asyncio.run(
            route_query("how many active clients does this company have in Italy?")
        )

    assert result.structured_query.model_dump() == {
        "intent": "count",
        "filters": {"region": "Italy", "status": "active"},
        "aggregation": "count",
        "domain": "customers",
        "sub_queries": [],
    }
    assert result.target_agent_ids == [ACME_AGENT]
