"""Benchmark aggregator tests with mocked IntelligenceAgent runs."""

from __future__ import annotations

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

from benchmark.aggregator import aggregate_sector_benchmark
from shared.models.intelligence import IntelligenceRunResult
from shared.models.routing import StructuredQuery


def _intel_result(count: int) -> IntelligenceRunResult:
    return IntelligenceRunResult(
        raw_insights=[
            {
                "aggregation": "count",
                "value": count,
                "metric": "record_count",
            }
        ],
        record_counts=[count],
    )


@pytest.mark.asyncio
async def test_aggregate_sector_benchmark_response_shape() -> None:
    structured = StructuredQuery(
        intent="benchmark",
        filters={"region": "Italy", "status": "active"},
        aggregation="count",
        domain="customers",
        mentioned_companies=["Acme Retail"],
    )

    counts = {
        "a0000000-0000-4000-8000-000000000001": 86,
        "a0000000-0000-4000-8000-000000000002": 68,
        "a0000000-0000-4000-8000-000000000003": 68,
    }

    async def fake_run(self: object) -> IntelligenceRunResult:
        company_id = self.company_id  # type: ignore[attr-defined]
        return _intel_result(counts[company_id])

    with patch(
        "benchmark.aggregator.IntelligenceAgent.run",
        new=fake_run,
    ):
        result = await aggregate_sector_benchmark(
            structured,
            raw_query="How does Acme Retail compare to the sector in Italy?",
        )

    response = str(result["response"])
    assert "Sector average:" in response
    assert "Italy" in response
    assert "above sector average" in response
    assert "Individual company results: private" in response
    assert "68" not in response
    assert "NordLogistics" not in response
    assert all(c >= 10 for c in result["record_counts"])


@pytest.mark.asyncio
async def test_aggregate_sector_benchmark_math_acme_16pct() -> None:
    structured = StructuredQuery(
        intent="benchmark",
        filters={"region": "Italy", "status": "active"},
        aggregation="count",
        domain="customers",
        mentioned_companies=["Acme Retail"],
    )

    async def fake_run(self: object) -> IntelligenceRunResult:
        company_id = self.company_id  # type: ignore[attr-defined]
        mapping = {
            "a0000000-0000-4000-8000-000000000001": 86,
            "a0000000-0000-4000-8000-000000000002": 68,
            "a0000000-0000-4000-8000-000000000003": 68,
        }
        return _intel_result(mapping[company_id])

    with (
        patch("benchmark.aggregator.IntelligenceAgent.run", new=fake_run),
        patch(
            "benchmark.aggregator.apply_benchmark_dp_noise",
            side_effect=lambda value, rng=None: int(value),
        ),
    ):
        result = await aggregate_sector_benchmark(structured)

    assert "Sector average: 74" in result["response"]
    assert "16% above" in result["response"]
