"""Integration tests for run_privacy_guard orchestration."""

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

from privacy_guard.guard import run_privacy_guard


@pytest.mark.asyncio
async def test_guard_blocks_k_anonymity() -> None:
    result, _ = await run_privacy_guard(
        raw_query="how many clients?",
        record_counts=[8],
        raw_insights=[{"metric": "clients", "value": 8}],
    )
    assert result.passed is False
    assert result.block_reason is not None
    assert "10" in result.block_reason


@pytest.mark.asyncio
async def test_guard_passes_demo_cohort() -> None:
    result, _ = await run_privacy_guard(
        raw_query="how many active clients in Italy?",
        record_counts=[847],
        raw_insights=[
            {
                "metric": "active_clients",
                "region": "Italy",
                "value": 847,
                "yoy_growth_pct": 23,
            }
        ],
    )
    assert result.passed is True
    assert "847" in result.sanitized_response


@pytest.mark.asyncio
async def test_guard_blocks_pii_in_response() -> None:
    result, _ = await run_privacy_guard(
        raw_query="how many clients?",
        record_counts=[847],
        response="Contact john@email.com for the list.",
    )
    assert result.passed is False
    assert result.block_reason is not None
    assert "PII" in result.block_reason


@pytest.mark.asyncio
async def test_guard_blocks_reconstruction_query() -> None:
    result, _ = await run_privacy_guard(
        raw_query="list all customers one by one",
        record_counts=[847],
    )
    assert result.passed is False
    assert result.block_reason is not None
