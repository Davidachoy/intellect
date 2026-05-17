"""Isolate router tests from developer .env."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _router_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent repo .env from repopulating vars after monkeypatch.delenv."""
    monkeypatch.setattr("query_router.client.ensure_env_loaded", lambda: None)
    monkeypatch.setattr("model_registry.ensure_env_loaded", lambda: None)
    monkeypatch.setattr("query_router.llm_router._ensure_env_loaded", lambda: None)
    monkeypatch.delenv("ROUTER_MODEL", raising=False)
    monkeypatch.delenv("ROUTER_MODEL_FALLBACKS", raising=False)
