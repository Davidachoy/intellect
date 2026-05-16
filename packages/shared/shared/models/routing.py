from typing import Any

from pydantic import BaseModel, Field


class StructuredQuery(BaseModel):
    """Parsed natural-language query for Intelligence Agents."""

    intent: str = Field(
        ...,
        description="Primary operation: count, average, percentage, sum, compare, trend, etc.",
    )
    filters: dict[str, Any] = Field(
        default_factory=dict,
        description="Extracted filters such as region, status, segment, date_range.",
    )
    aggregation: str = Field(
        ...,
        description="Aggregation to apply: count, average, percentage, sum, group_by_region.",
    )
    domain: str = Field(
        ...,
        description="Data domain: customers, shipments, clinical_trials, etc.",
    )
    sub_queries: list["StructuredQuery"] = Field(
        default_factory=list,
        description="Decomposed sub-queries for compound questions.",
    )


class RouterResult(BaseModel):
    structured_query: StructuredQuery
    target_agent_ids: list[str] = Field(
        ...,
        description="UUIDs of intelligence_agents rows to invoke.",
    )


StructuredQuery.model_rebuild()
