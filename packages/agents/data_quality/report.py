"""Build DataQualityReport from check issues."""

from __future__ import annotations

from shared.models.data_quality import (
    DataQualityIssue,
    DataQualityRecommendation,
    DataQualityReport,
)

_SEVERITY_PENALTY = {"low": 3, "medium": 8, "high": 15}


def build_report(issues: list[DataQualityIssue]) -> DataQualityReport:
    score = 100
    for issue in issues:
        score -= _SEVERITY_PENALTY.get(issue.severity, 5)
    score = max(0, min(100, score))

    if score < 60:
        recommendation = DataQualityRecommendation.REJECT
    elif score <= 80:
        recommendation = DataQualityRecommendation.REVIEW
    else:
        recommendation = DataQualityRecommendation.INGEST

    return DataQualityReport(
        score=score,
        issues=issues,
        recommendation=recommendation,
    )
