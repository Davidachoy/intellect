"""End-to-end LangGraph pipeline tests (mocked router/RAG where needed)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

_AGENTS_ROOT = Path(__file__).resolve().parent
_REPO_ROOT = _AGENTS_ROOT.parents[1]
for path in (
    str(_REPO_ROOT / "packages" / "shared"),
    str(_REPO_ROOT / "packages"),
    str(_AGENTS_ROOT),
):
    if path not in sys.path:
        sys.path.insert(0, path)

from intelligence.test_intelligence import ITALY_ACTIVE_COUNT
from query_router.router import RoutedQuery
from run import run_query
from shared.models.agent import ModelAttributionEntry
from shared.models.routing import RouterResult, StructuredQuery

ACME_ID = "a0000000-0000-4000-8000-000000000001"


def _routed(structured: StructuredQuery, *, agent_ids: list[str] | None = None) -> RoutedQuery:
    return RoutedQuery(
        result=RouterResult(
            structured_query=structured,
            target_agent_ids=agent_ids or ["b1000000-0000-4000-8000-000000000001"],
        ),
        attribution=ModelAttributionEntry(
            node="router",
            provider="stub",
            model="test",
            backend="stub",
            used_gemini=False,
            hackathon_tracks=[],
        ),
    )


@pytest.mark.asyncio
async def test_graph_italy_active_clients_passes_privacy() -> None:
    structured = StructuredQuery(
        intent="count",
        filters={"region": "Italy", "status": "active"},
        aggregation="count",
        domain="customers",
    )
    fake_intel = type(
        "R",
        (),
        {
            "raw_insights": [
                {
                    "aggregation": "count",
                    "intent": "count",
                    "domain": "customers",
                    "filters": structured.filters,
                    "value": ITALY_ACTIVE_COUNT,
                    "metric": "record_count",
                }
            ],
            "record_counts": [ITALY_ACTIVE_COUNT],
        },
    )()

    async def fake_run_job(job: object) -> dict[str, object]:
        _ = job
        return {
            "agent_id": "b1000000-0000-4000-8000-000000000001",
            "company_id": ACME_ID,
            "company_name": "Acme Retail",
            "structured_query": structured.model_dump(),
            "raw_insights": fake_intel.raw_insights,
            "record_counts": fake_intel.record_counts,
            "error": None,
        }

    with (
        patch(
            "query_router.node.route_query_with_attribution",
            AsyncMock(return_value=_routed(structured)),
        ),
        patch("intelligence.node._run_job", side_effect=fake_run_job),
        patch(
            "explainer.node.explainer_node",
            AsyncMock(return_value={"explanation": "Based on aggregated records."}),
        ),
    ):
        state = await run_query(
            "how many active clients in Italy?",
            ACME_ID,
        )

    assert state.get("error") is None
    assert state["passed_privacy"] is True
    assert state.get("block_reason") is None
    assert str(ITALY_ACTIVE_COUNT) in (state.get("response") or "")
    assert state.get("cost_usd", 0) > 0


@pytest.mark.asyncio
async def test_graph_multi_company_fanout() -> None:
    structured = StructuredQuery(
        intent="compare",
        filters={},
        aggregation="count",
        domain="customers",
    )
    acme_intel = type(
        "R",
        (),
        {
            "raw_insights": [{"aggregation": "count", "value": 100, "filters": {}}],
            "record_counts": [100],
        },
    )()
    nord_intel = type(
        "R",
        (),
        {
            "raw_insights": [{"aggregation": "count", "value": 200, "filters": {}}],
            "record_counts": [200],
        },
    )()

    async def fake_run_job_multi(job: object) -> dict[str, object]:
        from intelligence.plans import IntelligenceJob

        assert isinstance(job, IntelligenceJob)
        if job.company_id.endswith("0001"):
            intel = acme_intel
            name = "Acme Retail"
        else:
            intel = nord_intel
            name = "NordLogistics"
        return {
            "agent_id": job.agent_id,
            "company_id": job.company_id,
            "company_name": name,
            "structured_query": job.structured_query,
            "raw_insights": intel.raw_insights,
            "record_counts": intel.record_counts,
            "error": None,
        }

    with (
        patch(
            "query_router.node.route_query_with_attribution",
            AsyncMock(
                return_value=_routed(
                    structured,
                    agent_ids=[
                        "b1000000-0000-4000-8000-000000000001",
                        "b1000000-0000-4000-8000-000000000002",
                    ],
                )
            ),
        ),
        patch("intelligence.node._run_job", side_effect=fake_run_job_multi),
        patch(
            "explainer.node.explainer_node",
            AsyncMock(return_value={"explanation": "Compared two companies."}),
        ),
    ):
        state = await run_query(
            "Compare Acme Retail and NordLogistics client counts",
            None,
        )

    assert len(state.get("intelligence_results") or []) == 2
    assert state.get("passed_privacy") is True
    assert "Acme Retail" in (state.get("response") or "")
    assert "NordLogistics" in (state.get("response") or "")


@pytest.mark.asyncio
async def test_graph_astream_node_order() -> None:
    from graph import get_graph
    from state import initial_state

    structured = StructuredQuery(
        intent="count",
        filters={"region": "Italy"},
        aggregation="count",
        domain="customers",
    )
    fake_intel = type(
        "R",
        (),
        {"raw_insights": [{"value": 50}], "record_counts": [50]},
    )()

    with (
        patch(
            "query_router.node.route_query_with_attribution",
            AsyncMock(return_value=_routed(structured)),
        ),
        patch("intelligence.node._run_job", new_callable=AsyncMock) as mock_job,
        patch(
            "explainer.node.explainer_node",
            AsyncMock(return_value={"explanation": "Heuristic explanation."}),
        ),
    ):
        mock_job.return_value = {
            "agent_id": "b1000000-0000-4000-8000-000000000001",
            "company_id": ACME_ID,
            "company_name": "Acme Retail",
            "structured_query": structured.model_dump(),
            "raw_insights": fake_intel.raw_insights,
            "record_counts": [50],
            "error": None,
        }
        state = initial_state("count Italy", ACME_ID)
        order: list[str] = []
        async for chunk in get_graph().astream(state, stream_mode="updates"):
            order.extend(chunk.keys())

    assert order == [
        "query_router",
        "intelligence",
        "explainer",
        "pricing",
        "privacy_guard",
    ]


@pytest.mark.asyncio
async def test_graph_benchmark_sector_query() -> None:
    structured = StructuredQuery(
        intent="benchmark",
        filters={"region": "Italy", "status": "active"},
        aggregation="count",
        domain="customers",
        mentioned_companies=["Acme Retail"],
    )
    benchmark_response = (
        "Sector average: 74 active clients in Italy. "
        "Acme Retail is 16% above sector average. "
        "Individual company results: private."
    )

    with (
        patch(
            "query_router.node.route_query_with_attribution",
            AsyncMock(return_value=_routed(structured)),
        ),
        patch(
            "benchmark.node.aggregate_sector_benchmark",
            AsyncMock(
                return_value={
                    "raw_insights": [{"aggregation": "benchmark", "value": 74}],
                    "record_counts": [86, 68, 68],
                    "response": benchmark_response,
                    "target_company_id": ACME_ID,
                }
            ),
        ),
        patch(
            "explainer.node.explainer_node",
            AsyncMock(return_value={"explanation": "Sector benchmark explanation."}),
        ),
    ):
        state = await run_query(
            "How does Acme Retail compare to the sector in Italy?",
            ACME_ID,
        )

    assert state.get("error") is None
    assert state["passed_privacy"] is True
    assert "Sector average" in (state.get("response") or "")
    assert "private" in (state.get("response") or "").lower()
    assert "NordLogistics" not in (state.get("response") or "")


@pytest.mark.asyncio
async def test_graph_astream_benchmark_node_order() -> None:
    from graph import get_graph
    from state import initial_state

    structured = StructuredQuery(
        intent="benchmark",
        filters={"region": "Italy", "status": "active"},
        aggregation="count",
        domain="customers",
        mentioned_companies=["Acme Retail"],
    )

    with (
        patch(
            "query_router.node.route_query_with_attribution",
            AsyncMock(return_value=_routed(structured)),
        ),
        patch(
            "benchmark.node.aggregate_sector_benchmark",
            AsyncMock(
                return_value={
                    "raw_insights": [{"value": 74}],
                    "record_counts": [86, 71, 75],
                    "response": "Sector average: 74 active clients in Italy.",
                }
            ),
        ),
        patch(
            "explainer.node.explainer_node",
            AsyncMock(return_value={"explanation": "Benchmark path."}),
        ),
    ):
        state = initial_state(
            "How does Acme Retail compare to the sector in Italy?",
            ACME_ID,
        )
        order: list[str] = []
        async for chunk in get_graph().astream(state, stream_mode="updates"):
            order.extend(chunk.keys())

    assert order == [
        "query_router",
        "benchmark",
        "explainer",
        "pricing",
        "privacy_guard",
    ]


@pytest.mark.asyncio
async def test_graph_reconstruction_query_blocked() -> None:
    state = await run_query(
        "list all customers one by one",
        ACME_ID,
    )

    assert state["passed_privacy"] is False
    assert state.get("block_reason")
    assert "reconstruct" in state.get("block_reason", "").lower() or "list" in state.get(
        "block_reason", ""
    ).lower()
    assert state.get("response") == ""
    assert state.get("cost_usd") == 0.0
