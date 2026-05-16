from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class Company(BaseModel):
    id: UUID
    name: str
    api_key_hash: str
    created_at: datetime


class IntelligenceAgentConfig(BaseModel):
    access_rules: dict[str, object] = Field(default_factory=dict)
    sensitivity_tiers: dict[str, float] = Field(default_factory=dict)


class IntelligenceAgent(BaseModel):
    id: UUID
    company_id: UUID
    config: IntelligenceAgentConfig
    active: bool = True
    created_at: datetime
