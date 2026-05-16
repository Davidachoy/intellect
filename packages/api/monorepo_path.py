"""Ensure shared and agents packages are importable when running from packages/api."""

from __future__ import annotations

import sys
from pathlib import Path


def setup_monorepo_paths() -> None:
    root = Path(__file__).resolve().parents[2]
    for relative in ("packages/shared", "packages"):
        path = str(root / relative)
        if path not in sys.path:
            sys.path.insert(0, path)
