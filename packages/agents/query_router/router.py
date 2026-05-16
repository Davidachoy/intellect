from loguru import logger

from query_router.client import generate_router_output
from query_router.models import LLMRouterOutput, LLMSubQuery
from query_router.registry import resolve_agent_ids
from shared.models.routing import RouterResult, StructuredQuery


def _llm_sub_to_structured(sub: LLMSubQuery) -> StructuredQuery:
    return StructuredQuery(
        intent=sub.intent,
        filters=sub.filters,
        aggregation=sub.aggregation,
        domain=sub.domain,
        sub_queries=[],
    )


def _build_structured(llm: LLMRouterOutput) -> StructuredQuery:
    sub_queries = [_llm_sub_to_structured(s) for s in llm.sub_queries]
    return StructuredQuery(
        intent=llm.intent,
        filters=llm.filters,
        aggregation=llm.aggregation,
        domain=llm.domain,
        sub_queries=sub_queries,
    )


def _collect_target_agent_ids(
    structured: StructuredQuery,
    *,
    mentioned_companies: list[str],
    raw_query: str,
) -> list[str]:
    targets: list[str] = []

    targets.extend(
        resolve_agent_ids(
            domain=structured.domain,
            mentioned_companies=mentioned_companies,
            raw_query=raw_query,
        )
    )

    for sub in structured.sub_queries:
        targets.extend(
            resolve_agent_ids(
                domain=sub.domain,
                mentioned_companies=mentioned_companies,
                raw_query=raw_query,
            )
        )

    seen: set[str] = set()
    ordered: list[str] = []
    for agent_id in targets:
        if agent_id not in seen:
            seen.add(agent_id)
            ordered.append(agent_id)
    return ordered


async def route_query(raw_query: str) -> RouterResult:
    """Parse NL query via Gemini Flash and resolve target Intelligence Agents."""
    query = raw_query.strip()
    if not query:
        raise ValueError("raw_query must not be empty")

    logger.info("Routing query (len={})", len(query))
    llm_output = await generate_router_output(query)
    structured = _build_structured(llm_output)
    target_agent_ids = _collect_target_agent_ids(
        structured,
        mentioned_companies=llm_output.mentioned_companies,
        raw_query=query,
    )

    logger.info(
        "Router resolved domain={} agents={} sub_queries={}",
        structured.domain,
        target_agent_ids,
        len(structured.sub_queries),
    )

    return RouterResult(
        structured_query=structured,
        target_agent_ids=target_agent_ids,
    )
