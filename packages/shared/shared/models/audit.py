from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AuditEntry(BaseModel):
    id: UUID
    query_id: UUID
    agent: str
    event: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
