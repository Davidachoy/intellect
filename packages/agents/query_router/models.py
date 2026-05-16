from typing import Any, Literal

from pydantic import BaseModel, Field


class LLMSubQuery(BaseModel):
    intent: str
    filters: dict[str, Any] = Field(default_factory=dict)
    aggregation: str
    domain: str


class LLMRouterOutput(BaseModel):
    """Schema returned by Gemini Flash for routing."""

    intent: str
    filters: dict[str, Any] = Field(default_factory=dict)
    aggregation: str
    domain: str
    mentioned_companies: list[str] = Field(default_factory=list)
    complexity: Literal["simple", "compound"] = "simple"
    sub_queries: list[LLMSubQuery] = Field(default_factory=list)
