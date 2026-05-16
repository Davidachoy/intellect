"""Data Quality gate — runs before embeddings on POST /ingest."""

from __future__ import annotations

from typing import Any

from data_quality.checks import run_quality_checks
from data_quality.report import build_report
from loguru import logger
from shared.models.data_quality import DataQualityReport


async def run_data_quality_gate(
    documents: list[dict[str, Any]],
) -> DataQualityReport:
    """Evaluate ingest batch quality; async for LangGraph/API parity."""
    issues = run_quality_checks(documents)
    report = build_report(issues)
    logger.info(
        "data_quality: score={} recommendation={} issue_count={}",
        report.score,
        report.recommendation.value,
        len(report.issues),
    )
    return report
