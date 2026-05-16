from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    raw_query: str = Field(..., min_length=1)
    querier_api_key: str = Field(..., min_length=1)


class QueryResponse(BaseModel):
    query_id: str
    response: str
    blocked: bool
    block_reason: str | None = None
    cost_usd: float = Field(..., ge=0)
    sensitivity_tier: str
