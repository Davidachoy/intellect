from dataclasses import dataclass


@dataclass(frozen=True)
class AgentRegistryEntry:
    agent_id: str
    company_id: str
    company_name: str
    domain: str
    domain_aliases: frozenset[str]


# Demo registry aligned with packages/api/db/seed.sql
AGENT_REGISTRY: tuple[AgentRegistryEntry, ...] = (
    AgentRegistryEntry(
        agent_id="b1000000-0000-4000-8000-000000000001",
        company_id="a0000000-0000-4000-8000-000000000001",
        company_name="Acme Retail",
        domain="retail_customers",
        domain_aliases=frozenset(
            {
                "retail_customers",
                "customers",
                "customer",
                "clients",
                "client",
                "retail",
                "acme",
                "acme retail",
            }
        ),
    ),
    AgentRegistryEntry(
        agent_id="b1000000-0000-4000-8000-000000000002",
        company_id="a0000000-0000-4000-8000-000000000002",
        company_name="NordLogistics",
        domain="logistics_shipments",
        domain_aliases=frozenset(
            {
                "logistics_shipments",
                "shipments",
                "shipment",
                "logistics",
                "freight",
                "nordlogistics",
                "nord logistics",
            }
        ),
    ),
    AgentRegistryEntry(
        agent_id="b1000000-0000-4000-8000-000000000003",
        company_id="a0000000-0000-4000-8000-000000000003",
        company_name="MedResearch",
        domain="clinical_trials",
        domain_aliases=frozenset(
            {
                "clinical_trials",
                "trials",
                "trial",
                "clinical",
                "participants",
                "medresearch",
                "med research",
            }
        ),
    ),
)


def resolve_agent_ids(
    *,
    domain: str,
    mentioned_companies: list[str] | None = None,
    raw_query: str = "",
) -> list[str]:
    """Map domain and optional company mentions to intelligence agent UUIDs."""
    normalized_domain = domain.strip().lower().replace(" ", "_")
    if normalized_domain in ("none", "unsupported", ""):
        return []
    query_lower = raw_query.lower()
    mentioned = {name.strip().lower() for name in (mentioned_companies or [])}

    matched: list[str] = []

    for entry in AGENT_REGISTRY:
        if entry.company_name.lower() in mentioned:
            matched.append(entry.agent_id)
            continue
        if normalized_domain in entry.domain_aliases:
            matched.append(entry.agent_id)
            continue
        if entry.company_name.lower() in query_lower:
            matched.append(entry.agent_id)

    # Preserve registry order, dedupe
    seen: set[str] = set()
    ordered: list[str] = []
    for agent_id in matched:
        if agent_id not in seen:
            seen.add(agent_id)
            ordered.append(agent_id)
    return ordered


def lookup_agent(agent_id: str) -> AgentRegistryEntry | None:
    for entry in AGENT_REGISTRY:
        if entry.agent_id == agent_id:
            return entry
    return None


def lookup_company(company_id: str) -> AgentRegistryEntry | None:
    for entry in AGENT_REGISTRY:
        if entry.company_id == company_id:
            return entry
    return None


def company_id_for_agent(agent_id: str) -> str | None:
    entry = lookup_agent(agent_id)
    return entry.company_id if entry else None
