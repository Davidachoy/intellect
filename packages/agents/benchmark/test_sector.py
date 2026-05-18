"""Benchmark sector detection and formatting tests."""

from __future__ import annotations

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

from benchmark.sector import format_benchmark_response, sector_filters_for_company
from query_router.benchmark_intent import is_benchmark_query
from benchmark.sector import ACME_COMPANY_ID


@pytest.mark.parametrize(
    "query",
    [
        "How does Acme Retail compare to the sector in Italy?",
        "benchmark active clients in Italy",
        "Acme vs industry average in Italy",
    ],
)
def test_is_benchmark_query_positive(query: str) -> None:
    assert is_benchmark_query(query) is True


def test_is_benchmark_query_negative_simple_count() -> None:
    assert is_benchmark_query("how many active clients in Italy?") is False


def test_italy_sector_filter_mapping() -> None:
    assert sector_filters_for_company(
        ACME_COMPANY_ID, {"region": "Italy", "status": "active"}
    ) == {"region": "Italy", "status": "active"}
    assert sector_filters_for_company(
        "a0000000-0000-4000-8000-000000000002",
        {"region": "Italy"},
    ) == {"region": "Southern Europe"}


def test_format_benchmark_response() -> None:
    text = format_benchmark_response(
        sector_average=74,
        focal_company_name="Acme Retail",
        pct_vs_sector=16,
        region_label="Italy",
    )
    assert "Sector average: 74 active clients in Italy" in text
    assert "Acme Retail is 16% above sector average" in text
    assert "Individual company results: private" in text
    assert "NordLogistics" not in text
