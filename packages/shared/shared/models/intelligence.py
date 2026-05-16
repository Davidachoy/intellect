from typing import Any

from pydantic import BaseModel, Field


class AggregatedInsight(BaseModel):
    """Single aggregated metric — never a raw document row."""

    aggregation: str
    intent: str = ""
    domain: str = ""
    filters: dict[str, Any] = Field(default_factory=dict)
    value: int | float | None = None
    metric: str | None = None
    groups: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Grouped aggregates, e.g. region → count.",
    )
    extra: dict[str, Any] = Field(default_factory=dict)


class IntelligenceRunResult(BaseModel):
    raw_insights: list[dict[str, Any]]
    record_counts: list[int]
