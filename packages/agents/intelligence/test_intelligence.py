"""Unit tests for Intelligence Agent RAG — no live Supabase/Gemini required."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
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

from intelligence.aggregates import aggregate_payload_to_insight, build_run_result
from intelligence.base import IntelligenceAgent
from intelligence.rag import run_rag
from intelligence.store import ACME_RETAIL_COMPANY_ID
from shared.models.routing import StructuredQuery

ITALY_ACTIVE_COUNT = 86


@pytest.fixture
def acme_structured() -> StructuredQuery:
    return StructuredQuery(
        intent="count",
        filters={"region": "Italy", "status": "active"},
        aggregation="count",
        domain="customers",
    )


def test_aggregate_payload_never_exposes_raw_row_fields(
    acme_structured: StructuredQuery,
) -> None:
    payload = {
        "aggregation": "count",
        "record_count": ITALY_ACTIVE_COUNT,
        "filters": acme_structured.filters,
    }
    insight = aggregate_payload_to_insight(payload, acme_structured)
    dumped = insight.model_dump()
    assert "age" not in dumped
    assert "content" not in dumped
    assert "ltv_usd" not in dumped
    assert insight.value == ITALY_ACTIVE_COUNT


def test_group_by_region_aggregates_only(acme_structured: StructuredQuery) -> None:
    payload = {
        "aggregation": "group_by_region",
        "groups": [
            {"region": "Italy", "record_count": 100},
            {"region": "France", "record_count": 100},
        ],
        "record_count": 200,
        "filters": {},
    }
    structured = acme_structured.model_copy(
        update={"aggregation": "group_by_region", "filters": {}}
    )
    insight = aggregate_payload_to_insight(payload, structured)
    assert len(insight.groups) == 2
    assert all("region" in g and "record_count" in g for g in insight.groups)
    assert "age" not in insight.model_dump()


@pytest.mark.asyncio
async def test_run_rag_acme_italy_active_count(acme_structured: StructuredQuery) -> None:
    mock_aggregate = AsyncMock(
        return_value={
            "aggregation": "count",
            "record_count": ITALY_ACTIVE_COUNT,
            "filters": acme_structured.filters,
        }
    )
    mock_match = AsyncMock(return_value=["doc-1", "doc-2"])
    mock_embed = AsyncMock(return_value=[0.1] * 768)

    with (
        patch("intelligence.rag.run_aggregate", mock_aggregate),
        patch("intelligence.rag.match_document_ids", mock_match),
        patch("intelligence.rag.embed_text", mock_embed),
    ):
        result = await run_rag(ACME_RETAIL_COMPANY_ID, acme_structured)

    assert result.record_counts == [ITALY_ACTIVE_COUNT]
    assert len(result.raw_insights) == 1
    insight = result.raw_insights[0]
    assert insight["aggregation"] == "count"
    assert insight["value"] == ITALY_ACTIVE_COUNT
    assert "age" not in insight
    assert "content" not in insight

    mock_aggregate.assert_awaited_once()
    args, kwargs = mock_aggregate.await_args
    assert args[2] == acme_structured.filters
    assert kwargs.get("scope_ids") == ["doc-1", "doc-2"]


@pytest.mark.asyncio
async def test_intelligence_agent_run(acme_structured: StructuredQuery) -> None:
    agent = IntelligenceAgent(ACME_RETAIL_COMPANY_ID, acme_structured)
    fake_result = build_run_result(
        [
            aggregate_payload_to_insight(
                {
                    "aggregation": "count",
                    "record_count": ITALY_ACTIVE_COUNT,
                    "filters": acme_structured.filters,
                },
                acme_structured,
            )
        ]
    )

    with patch("intelligence.base.run_rag", AsyncMock(return_value=fake_result)):
        result = await agent.run()

    assert result.record_counts == [ITALY_ACTIVE_COUNT]
    assert result.raw_insights[0]["value"] == ITALY_ACTIVE_COUNT


def test_collect_record_counts_from_groups() -> None:
    structured = StructuredQuery(
        intent="count",
        filters={},
        aggregation="group_by_region",
        domain="customers",
    )
    payload: dict[str, Any] = {
        "aggregation": "group_by_region",
        "groups": [
            {"region": "Italy", "record_count": 12},
            {"region": "France", "record_count": 8},
        ],
        "record_count": 20,
    }
    result = build_run_result([aggregate_payload_to_insight(payload, structured)])
    assert 12 in result.record_counts
    assert 8 in result.record_counts
