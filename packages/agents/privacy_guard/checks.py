"""Deterministic privacy checks: k-anonymity, PII, reconstruction heuristics, DP noise."""

from __future__ import annotations

import random
import re

from shared.constants import K_ANONYMITY_THRESHOLD

_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    re.IGNORECASE,
)
_PHONE_RE = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
_UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_ID_LABEL_RE = re.compile(
    r"\b(?:customer|user|patient|client|member|employee|account)[-_ ]?id\s*[:=]\s*\S+",
    re.IGNORECASE,
)
_NAME_LIKE_RE = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b")

_RECONSTRUCTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\blist\s+all\b", re.IGNORECASE),
    re.compile(r"\bone\s+by\s+one\b", re.IGNORECASE),
    re.compile(r"\beach\s+(?:customer|client|patient|record|row)\b", re.IGNORECASE),
    re.compile(r"\bindividual\s+records?\b", re.IGNORECASE),
    re.compile(r"\bdump\s+(?:all|the)\b", re.IGNORECASE),
    re.compile(r"\bexport\s+all\b", re.IGNORECASE),
    re.compile(r"\benumerate\b", re.IGNORECASE),
    re.compile(r"\bde-?anonymi[sz]e\b", re.IGNORECASE),
    re.compile(r"\braw\s+(?:rows?|data|records?)\b", re.IGNORECASE),
)

_DP_NEAR_THRESHOLD_BAND = 10


def check_k_anonymity(
    record_counts: list[int],
    *,
    threshold: int = K_ANONYMITY_THRESHOLD,
) -> bool:
    """Return True when every count meets k-anonymity (>= threshold)."""
    if not record_counts:
        return True
    return all(count >= threshold for count in record_counts)


def _scrub_allowed_company_names(text: str) -> str:
    try:
        from query_router.registry import AGENT_REGISTRY

        scrubbed = text
        for entry in AGENT_REGISTRY:
            scrubbed = scrubbed.replace(entry.company_name, "[company]")
        return scrubbed
    except ImportError:
        return text


def check_pii(response: str) -> bool:
    """Return True when the response text contains no detectable PII."""
    if not response.strip():
        return True
    scrubbed = _scrub_allowed_company_names(response)
    if _EMAIL_RE.search(scrubbed):
        return False
    if _PHONE_RE.search(scrubbed):
        return False
    if _UUID_RE.search(scrubbed):
        return False
    if _SSN_RE.search(scrubbed):
        return False
    if _ID_LABEL_RE.search(scrubbed):
        return False
    if _NAME_LIKE_RE.search(scrubbed):
        return False
    return True


def check_reconstruction(query: str) -> bool:
    """Return True when the query is safe (not a reconstruction attempt). Heuristic fallback."""
    lowered = query.strip()
    if not lowered:
        return True
    return not any(pattern.search(lowered) for pattern in _RECONSTRUCTION_PATTERNS)


def apply_dp_noise_to_counts(
    record_counts: list[int],
    *,
    threshold: int = K_ANONYMITY_THRESHOLD,
    band: int = _DP_NEAR_THRESHOLD_BAND,
) -> list[int]:
    """Add small noise to counts near the k-anonymity threshold (differential privacy)."""
    adjusted: list[int] = []
    for count in record_counts:
        if threshold <= count < threshold + band:
            noise = int(round(random.gauss(0, 2)))
            adjusted.append(max(threshold, count + noise))
        else:
            adjusted.append(count)
    return adjusted
