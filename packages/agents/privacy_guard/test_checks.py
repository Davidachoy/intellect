"""Privacy Guard unit tests — deterministic checks, no Featherless API required."""

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

from privacy_guard.checks import check_k_anonymity, check_pii, check_reconstruction


def test_k_anonymity_blocks_small_cohort() -> None:
    assert check_k_anonymity([8]) is False


def test_k_anonymity_passes_large_cohort() -> None:
    assert check_k_anonymity([847]) is True


def test_pii_blocks_email() -> None:
    assert check_pii("Please contact john@email.com for details.") is False


def test_pii_passes_aggregated_text() -> None:
    assert check_pii("847 active clients in Italy, 23% YoY growth") is True


def test_pii_allows_registered_company_names() -> None:
    assert check_pii("Acme Retail: 847 active clients in Italy.") is True
    assert check_pii("NordLogistics: 120 records in Italy.") is True


def test_reconstruction_blocks_enumeration_query() -> None:
    assert check_reconstruction("list all customers one by one") is False


def test_reconstruction_passes_aggregated_query() -> None:
    assert check_reconstruction("how many active clients in Italy?") is True
