from dataclasses import dataclass

from loguru import logger

from privacy_guard.checks import check_reconstruction
from query_router.client import generate_router_output
from query_router.generation import RouterGenerationResult
from query_router.llm_parse import is_out_of_scope_output
from query_router.models import LLMRouterOutput, LLMSubQuery
from query_router.registry import resolve_agent_ids
from shared.models.agent import ModelAttributionEntry
from shared.models.routing import RouterResult, StructuredQuery


@dataclass(frozen=True)
class RoutedQuery:
    result: RouterResult
    attribution: ModelAttributionEntry


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


def _build_routed(generation: RouterGenerationResult, *, raw_query: str) -> RoutedQuery:
    llm_output = generation.output
    structured = _build_structured(llm_output)
    target_agent_ids = _collect_target_agent_ids(
        structured,
        mentioned_companies=llm_output.mentioned_companies,
        raw_query=raw_query,
    )
    if is_out_of_scope_output(llm_output):
        logger.info("Router marked query as out-of-scope (intent=unsupported)")
    else:
        logger.info(
            "Router resolved domain={} agents={} sub_queries={} gemini={}",
            structured.domain,
            target_agent_ids,
            len(structured.sub_queries),
            generation.attribution.used_gemini,
        )
    return RoutedQuery(
        result=RouterResult(
            structured_query=structured,
            target_agent_ids=target_agent_ids,
        ),
        attribution=generation.attribution,
    )


def _in_scope_reconstruction_route(raw_query: str) -> LLMRouterOutput | None:
    """Route reconstruction attempts as in-scope so Privacy Guard can block them."""
    if check_reconstruction(raw_query):
        return None
    return LLMRouterOutput(
        intent="list",
        filters={},
        aggregation="none",
        domain="customers",
        mentioned_companies=[],
        complexity="simple",
        sub_queries=[],
    )


async def route_query_with_attribution(raw_query: str) -> RoutedQuery:
    """Parse NL query; returns routing result plus model attribution for audit/demo."""
    query = raw_query.strip()
    if not query:
        raise ValueError("raw_query must not be empty")

    logger.info("Routing query (len={})", len(query))

    forced = _in_scope_reconstruction_route(query)
    if forced is not None:
        from model_registry import attribution_from_invocation

        generation = RouterGenerationResult(
            output=forced,
            attribution=attribution_from_invocation(
                "router", model=None, backend="heuristic"
            ),
        )
        logger.info("Router flagged reconstruction-shaped query; routing in-scope for privacy")
        return _build_routed(generation, raw_query=query)

    generation = await generate_router_output(query)
    return _build_routed(generation, raw_query=query)


async def route_query(raw_query: str) -> RouterResult:
    """Parse NL query and resolve target Intelligence Agents."""
    return (await route_query_with_attribution(raw_query)).result
