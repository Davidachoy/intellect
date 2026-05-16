"""Intelligence Agent — company-scoped RAG over pgvector + aggregate SQL."""

from __future__ import annotations

from typing import Any

from loguru import logger

from intelligence.rag import run_rag
from shared.models.intelligence import IntelligenceRunResult
from shared.models.routing import StructuredQuery


class IntelligenceAgent:
    """Runs privacy-safe RAG for one company partition."""

    def __init__(
        self,
        company_id: str,
        structured_query: StructuredQuery | dict[str, Any],
        *,
        use_vector_scope: bool = True,
    ) -> None:
        self.company_id = company_id
        self.use_vector_scope = use_vector_scope
        if isinstance(structured_query, StructuredQuery):
            self.structured_query = structured_query
        else:
            self.structured_query = StructuredQuery.model_validate(structured_query)

    async def run(self) -> IntelligenceRunResult:
        logger.info(
            "IntelligenceAgent company_id={} intent={} aggregation={}",
            self.company_id,
            self.structured_query.intent,
            self.structured_query.aggregation,
        )
        return await run_rag(
            self.company_id,
            self.structured_query,
            use_vector_scope=self.use_vector_scope,
        )
