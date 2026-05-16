"""Data quality checks before embedding: empties, duplicates, outliers, PII."""

from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Any

from privacy_guard.checks import check_pii
from shared.models.data_quality import DataQualityIssue

_EMAIL_IN_CONTENT = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    re.IGNORECASE,
)
_PHONE_IN_CONTENT = re.compile(
    r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
)


def _content_has_pii(text: str) -> bool:
    if not check_pii(text):
        return True
    if _EMAIL_IN_CONTENT.search(text):
        return True
    if _PHONE_IN_CONTENT.search(text):
        return True
    return False


def _is_empty_document(content: str, metadata: dict[str, Any]) -> bool:
    if not content.strip():
        return True
    if not metadata:
        return False
    scalar_values = [
        v
        for v in metadata.values()
        if isinstance(v, (str, int, float)) and str(v).strip()
    ]
    return len(scalar_values) == 0 and not any(
        isinstance(v, (dict, list)) and v for v in metadata.values()
    )


def _collect_numeric_metadata(
    documents: list[dict[str, Any]],
) -> dict[str, list[tuple[int, float]]]:
    by_field: dict[str, list[tuple[int, float]]] = defaultdict(list)
    for idx, doc in enumerate(documents):
        meta = doc.get("metadata") or {}
        if not isinstance(meta, dict):
            continue
        for key, value in meta.items():
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)):
                by_field[str(key)].append((idx, float(value)))
            elif isinstance(value, str):
                try:
                    by_field[str(key)].append((idx, float(value)))
                except ValueError:
                    continue
    return by_field


def run_quality_checks(documents: list[dict[str, Any]]) -> list[DataQualityIssue]:
    """Run all ingest checks; return detected issues."""
    issues: list[DataQualityIssue] = []
    content_keys: dict[str, int] = {}

    for idx, doc in enumerate(documents):
        content = str(doc.get("content") or "")
        metadata = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}

        if _is_empty_document(content, metadata):
            issues.append(
                DataQualityIssue(
                    issue_type="empty_field",
                    message="Document has empty content or only empty metadata values",
                    severity="high",
                    document_index=idx,
                )
            )

        normalized = content.strip().lower()
        if normalized:
            if normalized in content_keys:
                issues.append(
                    DataQualityIssue(
                        issue_type="duplicate_record",
                        message="Duplicate document content detected",
                        severity="medium",
                        document_index=idx,
                        field=f"duplicate_of_index_{content_keys[normalized]}",
                    )
                )
            else:
                content_keys[normalized] = idx

        if _content_has_pii(content):
            issues.append(
                DataQualityIssue(
                    issue_type="pii_in_content",
                    message="Potential PII detected in document content",
                    severity="high",
                    document_index=idx,
                )
            )

    for field, values in _collect_numeric_metadata(documents).items():
        if len(values) < 3:
            continue
        nums = [v for _, v in values]
        mean = sum(nums) / len(nums)
        variance = sum((x - mean) ** 2 for x in nums) / len(nums)
        std = math.sqrt(variance)
        if std <= 0:
            continue
        for doc_idx, value in values:
            if abs(value - mean) > 3 * std:
                issues.append(
                    DataQualityIssue(
                        issue_type="outlier",
                        message=(
                            f"Metadata field '{field}' value {value} exceeds "
                            f"3 standard deviations from mean ({mean:.2f})"
                        ),
                        severity="medium",
                        document_index=doc_idx,
                        field=field,
                    )
                )

    return issues
