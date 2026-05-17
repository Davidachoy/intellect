"""Gemini model resolution and dispatch tests (mocked)."""

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

from query_router.client import generate_router_output, resolve_model_chain
from query_router.models import LLMRouterOutput


def test_resolve_primary_and_fallbacks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ROUTER_MODE", "auto")
    monkeypatch.setenv("ROUTER_MODEL", "gemini-3-flash-preview")
    monkeypatch.setenv("ROUTER_MODEL_FALLBACKS", "gemini-3.1-flash-lite")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    assert resolve_model_chain() == ["gemini-3-flash-preview", "gemini-3.1-flash-lite"]


def test_legacy_provider_alias_maps_to_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ROUTER_PROVIDER", "google")
    monkeypatch.setenv("ROUTER_MODEL", "")
    monkeypatch.setenv("ROUTER_MODE", "")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    assert resolve_model_chain() == ["gemini-3-flash-preview"]


def test_auto_default_chain_when_no_model_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ROUTER_MODE", "auto")
    monkeypatch.setenv("ROUTER_MODEL", "")
    monkeypatch.setenv("ROUTER_MODEL_FALLBACKS", "")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    chain = resolve_model_chain()
    assert chain == ["gemini-3-flash-preview"]


def test_heuristic_mode_empty_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ROUTER_MODE", "heuristic")
    assert resolve_model_chain() == []


@pytest.mark.asyncio
async def test_generate_router_output_calls_gemini(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ROUTER_MODE", "auto")
    monkeypatch.setenv("ROUTER_MODEL", "gemini-3-flash-preview")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    llm_output = LLMRouterOutput(
        intent="count",
        filters={"region": "Italy"},
        aggregation="count",
        domain="customers",
    )
    with patch(
        "query_router.client.generate_llm_router_output",
        new_callable=AsyncMock,
        return_value=llm_output,
    ) as mock_llm:
        generation = await generate_router_output("clients in Italy")
    mock_llm.assert_awaited_once_with("clients in Italy", model="gemini-3-flash-preview")
    assert generation.output.domain == "customers"
    assert generation.attribution.node == "router"
