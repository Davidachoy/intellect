"""Detect sector / cross-company benchmark queries (no benchmark package imports)."""

from __future__ import annotations

import re

_BENCHMARK_PATTERN = re.compile(
    r"\b("
    r"compare|comparison|comparing|versus|vs\.?|benchmark|sector|industry|"
    r"how\s+does|against\s+the\s+sector|cross[- ]company|peer\s+group"
    r")\b",
    re.IGNORECASE,
)


def is_benchmark_query(text: str) -> bool:
    """True when the NL query asks for sector / cross-company comparison."""
    lowered = text.strip().lower()
    if not lowered or not _BENCHMARK_PATTERN.search(lowered):
        return False
    if "sector" in lowered or "industry" in lowered or "benchmark" in lowered:
        return True
    if re.search(r"\bcompare\b", lowered):
        return True
    return bool(re.search(r"\b(how\s+does|vs\.?|versus)\b", lowered))
