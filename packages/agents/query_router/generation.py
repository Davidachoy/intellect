from dataclasses import dataclass

from query_router.models import LLMRouterOutput
from shared.models.agent import ModelAttributionEntry


@dataclass(frozen=True)
class RouterGenerationResult:
    output: LLMRouterOutput
    attribution: ModelAttributionEntry
