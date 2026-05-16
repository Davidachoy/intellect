from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

AnomalySeverity = Literal["low", "medium", "high"]


class AnomalyAlert(BaseModel):
    id: UUID
    querier_id: str
    pattern: str
    query_ids: list[UUID]
    severity: AnomalySeverity
    created_at: datetime
    acknowledged: bool = False


class AnomalyAlertCreate(BaseModel):
    querier_id: str
    pattern: str
    query_ids: list[UUID]
    severity: AnomalySeverity
