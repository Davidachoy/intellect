"""Pytest path setup for agents package tests."""

from __future__ import annotations

import sys
from pathlib import Path

_AGENTS_ROOT = Path(__file__).resolve().parent
_REPO_ROOT = _AGENTS_ROOT.parents[1]
for path in (
    str(_REPO_ROOT / "packages" / "shared"),
    str(_REPO_ROOT / "packages"),
    str(_AGENTS_ROOT),
):
    if path not in sys.path:
        sys.path.insert(0, path)
