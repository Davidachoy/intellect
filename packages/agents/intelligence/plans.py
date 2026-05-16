"""Build intelligence fan-out jobs from router state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from query_router.registry import (
    AGENT_REGISTRY,
    lookup_agent,
    lookup_company,
    resolve_agent_ids,
)

DEFAULT_COMPANY_ID = "a0000000-0000-4000-8000-000000000001"


@dataclass(frozen=True)
class IntelligenceJob:
    agent_id: str
    company_id: str
    company_name: str
    structured_query: dict[str, Any]


def _structured_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return value
    return {}


def build_intelligence_jobs(
    *,
    structured_query: dict[str, Any],
    target_agent_ids: list[str],
    target_company_id: str,
    raw_query: str,
) -> list[IntelligenceJob]:
    """Resolve which company partitions to query and with which structured query."""
    structured = _structured_dict(structured_query)
    sub_queries = structured.get("sub_queries") or []
    jobs: list[IntelligenceJob] = []

    if sub_queries:
        for index, sub in enumerate(sub_queries):
            sq = _structured_dict(sub)
            domain = str(sq.get("domain") or structured.get("domain") or "")
            agent_ids = _agent_ids_for_sub_query(
                index=index,
                domain=domain,
                target_agent_ids=target_agent_ids,
                target_company_id=target_company_id,
            )
            for agent_id in agent_ids:
                entry = lookup_agent(agent_id)
                if entry:
                    jobs.append(
                        IntelligenceJob(
                            agent_id=entry.agent_id,
                            company_id=entry.company_id,
                            company_name=entry.company_name,
                            structured_query=sq,
                        )
                    )
        return _dedupe_jobs(jobs)

    if target_agent_ids:
        for agent_id in target_agent_ids:
            entry = lookup_agent(agent_id)
            if entry:
                jobs.append(
                    IntelligenceJob(
                        agent_id=entry.agent_id,
                        company_id=entry.company_id,
                        company_name=entry.company_name,
                        structured_query=structured,
                    )
                )
        if jobs:
            return _dedupe_jobs(jobs)

    if target_company_id:
        entry = lookup_company(target_company_id)
        if entry:
            return [
                IntelligenceJob(
                    agent_id=entry.agent_id,
                    company_id=entry.company_id,
                    company_name=entry.company_name,
                    structured_query=structured,
                )
            ]

    default = lookup_company(DEFAULT_COMPANY_ID) or AGENT_REGISTRY[0]
    return [
        IntelligenceJob(
            agent_id=default.agent_id,
            company_id=default.company_id,
            company_name=default.company_name,
            structured_query=structured,
        )
    ]


def _agent_ids_for_sub_query(
    *,
    index: int,
    domain: str,
    target_agent_ids: list[str],
    target_company_id: str,
) -> list[str]:
    """Map one sub-query to at most one intelligence agent (no compare fan-out)."""
    if index < len(target_agent_ids):
        return [target_agent_ids[index]]
    # Domain-only: omit raw_query/mentions or each sub-query matches every company.
    by_domain = resolve_agent_ids(domain=domain)
    if by_domain:
        return [by_domain[0]]
    if target_company_id:
        entry = lookup_company(target_company_id)
        if entry:
            return [entry.agent_id]
    return []


def _dedupe_jobs(jobs: list[IntelligenceJob]) -> list[IntelligenceJob]:
    seen: set[str] = set()
    ordered: list[IntelligenceJob] = []
    for job in jobs:
        if job.agent_id in seen:
            continue
        seen.add(job.agent_id)
        ordered.append(job)
    return ordered
