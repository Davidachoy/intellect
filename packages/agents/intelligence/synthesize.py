"""Merge multi-company aggregated insights into one narrative (no raw rows)."""

from __future__ import annotations

from typing import Any


def _format_insight_segment(insight: dict[str, Any], *, company_name: str) -> str:
    value = insight.get("value")
    filters = insight.get("filters") or {}
    region = insight.get("region") or filters.get("region")
    status = filters.get("status")
    growth = insight.get("yoy_growth_pct")
    aggregation = (insight.get("aggregation") or "").lower()

    if aggregation == "count" and value is not None:
        label = "active clients" if status == "active" else "records"
        segment = f"{value:,} {label}" if isinstance(value, int) else f"{value} {label}"
        if region:
            segment += f" in {region}"
    else:
        metric = insight.get("metric", "metric")
        segment = f"{metric}: {value}" if value is not None else str(metric)
        if region:
            segment += f" (region={region})"

    if growth is not None:
        segment += f", {growth}% YoY growth"

    if company_name:
        return f"{company_name}: {segment}"
    return segment


def synthesize_multi_company_response(
    intelligence_results: list[dict[str, Any]],
) -> str:
    """Build a single response string from per-company intelligence runs."""
    if not intelligence_results:
        return ""

    multi = len(intelligence_results) > 1
    parts: list[str] = []
    for result in intelligence_results:
        company_name = str(result.get("company_name") or "Unknown")
        label = company_name if multi else ""
        error = result.get("error")
        if error:
            prefix = f"{company_name}: " if multi else ""
            parts.append(f"{prefix}unavailable ({error})")
            continue

        insights = result.get("raw_insights") or []
        if not insights:
            prefix = f"{company_name}: " if multi else ""
            parts.append(f"{prefix}no aggregated insight available")
            continue

        for insight in insights:
            tagged = dict(insight)
            tagged.setdefault("company_name", company_name)
            display_name = company_name if multi else ""
            parts.append(_format_insight_segment(tagged, company_name=display_name))

    return ". ".join(parts) + ("." if parts else "")
