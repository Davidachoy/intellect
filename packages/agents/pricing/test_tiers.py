"""Unit tests for pricing tier lookup."""

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

from pricing.tiers import (
    calculate_cost,
    cost_for_tier,
    resolve_sensitivity_tier,
)


@pytest.mark.parametrize(
    ("tier", "expected"),
    [
        ("public", 0.0),
        ("aggregated", 0.01),
        ("sensitive", 0.05),
        ("strategic", 0.25),
    ],
)
def test_cost_for_tier(tier: str, expected: float) -> None:
    assert cost_for_tier(tier) == expected


def test_cost_for_unknown_tier_defaults_to_aggregated() -> None:
    assert cost_for_tier("unknown") == 0.01


def test_resolve_public_for_unsupported_intent() -> None:
    assert resolve_sensitivity_tier({"intent": "unsupported"}) == "public"


def test_resolve_strategic_for_benchmark_intent() -> None:
    sq = {"intent": "benchmark", "domain": "customers"}
    assert resolve_sensitivity_tier(sq) == "strategic"


def test_resolve_strategic_for_compound_sub_queries() -> None:
    sq = {
        "intent": "compare",
        "domain": "customers",
        "sub_queries": [{"domain": "a"}, {"domain": "b"}],
    }
    assert resolve_sensitivity_tier(sq) == "strategic"


def test_resolve_sensitive_for_customer_domain() -> None:
    assert resolve_sensitivity_tier({"intent": "count", "domain": "customers"}) == (
        "sensitive"
    )


def test_calculate_cost_multiplies_compound_sub_queries() -> None:
    sq = {
        "sub_queries": [
            {"domain": "customers"},
            {"domain": "logistics_shipments"},
        ],
    }
    assert calculate_cost("sensitive", sq) == pytest.approx(0.10)
