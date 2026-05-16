"""Model chain resolution and LiteLLM dispatch tests (mocked)."""

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

from model_registry import attribution_from_invocation
from query_router.client import generate_router_output, resolve_model_chain
from query_router.generation import RouterGenerationResult
from query_router.models import LLMRouterOutput


def test_resolve_primary_and_fallbacks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ROUTER_MODE", "auto")
    monkeypatch.setenv("ROUTER_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("ROUTER_MODEL_FALLBACKS", "claude-3-5-haiku-latest")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    assert resolve_model_chain() == ["gpt-4o-mini", "claude-3-5-haiku-latest"]


def test_legacy_provider_alias_maps_to_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ROUTER_PROVIDER", "claude")
    monkeypatch.delenv("ROUTER_MODEL", raising=False)
    monkeypatch.delenv("ROUTER_MODE", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    assert resolve_model_chain() == ["claude-3-5-haiku-latest"]


def test_auto_default_chain_when_no_model_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ROUTER_MODE", "auto")
    monkeypatch.delenv("ROUTER_MODEL", raising=False)
    monkeypatch.delenv("ROUTER_MODEL_FALLBACKS", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    chain = resolve_model_chain()
    assert chain == ["gpt-4o-mini"]


def test_heuristic_mode_empty_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ROUTER_MODE", "heuristic")
    assert resolve_model_chain() == []


@pytest.mark.asyncio
async def test_generate_router_output_calls_litellm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ROUTER_MODE", "auto")
    monkeypatch.setenv("ROUTER_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
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
    mock_llm.assert_awaited_once_with("clients in Italy", model="gpt-4o-mini")
    assert generation.output.domain == "customers"
    assert generation.attribution.node == "router"
