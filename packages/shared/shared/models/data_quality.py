from enum import Enum

from pydantic import BaseModel, Field


class DataQualityRecommendation(str, Enum):
    INGEST = "ingest"
    REVIEW = "review"
    REJECT = "reject"


class DataQualityIssue(BaseModel):
    issue_type: str
    message: str
    severity: str = Field(..., description="low | medium | high")
    field: str | None = None
    document_index: int | None = None


class DataQualityReport(BaseModel):
    score: int = Field(..., ge=0, le=100)
    issues: list[DataQualityIssue] = Field(default_factory=list)
    recommendation: DataQualityRecommendation
