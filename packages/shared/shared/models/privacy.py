from pydantic import BaseModel, Field


class PrivacyGuardResult(BaseModel):
    """Outcome of all privacy checks before a response may leave the system."""

    passed: bool
    block_reason: str | None = None
    sanitized_response: str = ""
    record_counts: list[int] = Field(
        default_factory=list,
        description="Counts after optional DP noise near the k-anonymity threshold",
    )
