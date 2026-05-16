from pydantic import BaseModel, Field


class ModelAttributionEntry(BaseModel):
    """Which model/backend powered a graph node — for demos, audit, and hackathon tracks."""

    node: str
    provider: str = Field(
        ...,
        description="google | openai | anthropic | heuristic | featherless | stub | unknown",
    )
    model: str | None = Field(
        default=None,
        description="LiteLLM model id or Featherless catalog id; null for heuristic.",
    )
    backend: str = Field(
        ...,
        description="litellm | heuristic | featherless | speechmatics | stub",
    )
    hackathon_tracks: list[str] = Field(
        default_factory=list,
        description="Sponsor tracks this node satisfies, e.g. google_gemini, featherless.",
    )
    used_gemini: bool = Field(
        default=False,
        description="True when Google Gemini was the configured or invoked model.",
    )
