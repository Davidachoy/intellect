from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class IngestDocument(BaseModel):
    content: str = Field(..., min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestRequest(BaseModel):
    company_id: UUID
    owner_api_key: str = Field(..., min_length=1)
    documents: list[IngestDocument] = Field(..., min_length=1, max_length=500)


class IngestResponse(BaseModel):
    company_id: UUID
    document_ids: list[str]
    ingested_count: int = Field(..., ge=0)
    data_quality_score: int | None = Field(
        default=None,
        ge=0,
        le=100,
        description="0-100 quality score from Data Quality Agent.",
    )
    data_quality_warning: str | None = Field(
        default=None,
        description="Present when score is 60-80 (ingest with review).",
    )
