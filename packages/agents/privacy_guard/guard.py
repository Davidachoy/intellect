"""Orchestrates all privacy checks into a single typed result."""

from __future__ import annotations

from loguru import logger

from privacy_guard.checks import (
    apply_dp_noise_to_counts,
    check_k_anonymity,
    check_pii,
)
from model_registry import attribution_from_invocation
from privacy_guard.client import classify_reconstruction_with_featherless
from shared.constants import K_ANONYMITY_THRESHOLD
from shared.models.agent import ModelAttributionEntry
from shared.models.privacy import PrivacyGuardResult


def _candidate_response(
    *,
    response: str,
    sanitized_response: str,
    raw_insights: list[dict],
) -> str:
    if response.strip():
        return response.strip()
    if sanitized_response.strip():
        return sanitized_response.strip()
    if not raw_insights:
        return ""
    parts: list[str] = []
    for insight in raw_insights:
        value = insight.get("value")
        filters = insight.get("filters") or {}
        region = insight.get("region") or filters.get("region")
        status = filters.get("status")
        growth = insight.get("yoy_growth_pct")
        aggregation = insight.get("aggregation", "")

        if aggregation == "count" and value is not None:
            label = "active clients" if status == "active" else "records"
            segment = f"{value} {label}"
            if region:
                segment += f" in {region}"
        else:
            metric = insight.get("metric", "metric")
            segment = f"{metric}: {value}" if value is not None else str(metric)
            if region:
                segment += f" (region={region})"

        if growth is not None:
            segment += f", {growth}% YoY growth"
        parts.append(segment)
    return "; ".join(parts)


async def run_privacy_guard(
    *,
    raw_query: str,
    record_counts: list[int],
    response: str = "",
    sanitized_response: str = "",
    raw_insights: list[dict] | None = None,
    skip_reconstruction: bool = False,
) -> tuple[PrivacyGuardResult, ModelAttributionEntry]:
    """Run k-anonymity, PII, and reconstruction checks (never skipped)."""
    insights = raw_insights or []
    noisy_counts = apply_dp_noise_to_counts(list(record_counts))
    candidate = _candidate_response(
        response=response,
        sanitized_response=sanitized_response,
        raw_insights=insights,
    )

    if not check_k_anonymity(noisy_counts):
        min_count = min(noisy_counts) if noisy_counts else 0
        reason = (
            f"Response blocked: fewer than {K_ANONYMITY_THRESHOLD} records in cohort "
            f"(count={min_count})"
        )
        logger.warning("privacy_guard blocked: {}", reason)
        return (
            PrivacyGuardResult(
                passed=False,
                block_reason=reason,
                sanitized_response="",
                record_counts=noisy_counts,
            ),
            attribution_from_invocation("privacy_guard", model=None, backend="heuristic"),
        )

    if not check_pii(candidate):
        reason = "PII detected in response (email, phone, ID, or name-like text)"
        logger.warning("privacy_guard blocked: {}", reason)
        return (
            PrivacyGuardResult(
                passed=False,
                block_reason=reason,
                sanitized_response="",
                record_counts=noisy_counts,
            ),
            attribution_from_invocation("privacy_guard", model=None, backend="heuristic"),
        )

    if skip_reconstruction:
        attribution = attribution_from_invocation(
            "privacy_guard", model=None, backend="heuristic"
        )
        safe, recon_reason = True, None
    else:
        safe, recon_reason, attribution = await classify_reconstruction_with_featherless(
            raw_query
        )
    if not safe:
        reason = recon_reason or "Query appears designed to reconstruct individual records"
        logger.warning("privacy_guard blocked: {}", reason)
        return (
            PrivacyGuardResult(
                passed=False,
                block_reason=reason,
                sanitized_response="",
                record_counts=noisy_counts,
            ),
            attribution,
        )

    logger.info(
        "privacy_guard passed record_counts={} response_len={}",
        noisy_counts,
        len(candidate),
    )
    return (
        PrivacyGuardResult(
            passed=True,
            block_reason=None,
            sanitized_response=candidate,
            record_counts=noisy_counts,
        ),
        attribution,
    )
