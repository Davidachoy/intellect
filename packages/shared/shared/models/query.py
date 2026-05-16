from uuid import UUID

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    raw_query: str = Field(..., min_length=1)
    querier_api_key: str = Field(..., min_length=1)
    target_company_id: UUID | None = Field(
        default=None,
        description="Optional data owner; omit to auto-route via Query Router.",
    )


class QueryResponse(BaseModel):
    query_id: str
    response: str
    blocked: bool
    block_reason: str | None = None
    cost_usd: float = Field(..., ge=0)
    sensitivity_tier: str
    explanation: str | None = Field(
        default=None,
        description="Plain-English derivation summary from Query Explainer.",
    )
