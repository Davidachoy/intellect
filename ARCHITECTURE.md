# Intellect — Architecture

## Overview

Intellect is a multi-agent intelligence brokerage. Companies register an Intelligence Agent backed by their own private vector store. External parties query in natural language and receive aggregated insights. Raw data never leaves the owning company's agent. Every query passes through a Privacy Guard before any response is returned.

```
Querier (text or voice)
        │
        ▼
┌───────────────────┐
│   API Gateway     │  FastAPI — auth, rate limiting, audit logging
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  Query Router     │  LangGraph node — Gemini Flash
│  Agent            │  NL → structured query → selects target agent(s)
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  Intelligence     │  One per registered company
│  Agent(s)         │  RAG over private pgvector store
│                   │  Returns aggregated insight only
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  Privacy Guard    │  Featherless open-source model
│  Agent            │  k-anonymity ≥ 10, PII strip, block reconstruction
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  Pricing Agent    │  Calculates cost, logs transaction
└────────┬──────────┘
         │
         ▼
   Response to Querier
   { insight, cost, query_id }

```

---

## Package Structure

### `packages/api/`

FastAPI application. HTTP layer only — no business logic here.

```
api/
├── main.py                  ← app entry point
├── routes/
│   ├── queries.py           ← POST /query
│   ├── companies.py         ← POST /companies (register)
│   └── audit.py             ← GET /audit/{query_id}
├── middleware/
│   ├── auth.py              ← API key validation
│   └── logging.py           ← request/response logging
└── dependencies.py          ← shared FastAPI deps

```

### `packages/agents/`

LangGraph graph and all agent nodes.

```
agents/
├── graph.py                 ← LangGraph graph definition
├── state.py                 ← QueryState TypedDict
├── query_router/
│   ├── node.py              ← router agent node
│   └── prompts.py           ← Gemini prompts
├── privacy_guard/
│   ├── node.py              ← privacy guard node
│   ├── checks.py            ← k-anonymity, PII detection
│   └── prompts.py           ← Featherless prompts
├── pricing/
│   ├── node.py              ← pricing node
│   └── tiers.py             ← sensitivity tier definitions
└── intelligence/
    ├── base.py              ← base Intelligence Agent class
    ├── rag.py               ← RAG over pgvector
    └── prompts.py

```

### `packages/shared/`

Pydantic models and constants shared across packages.

```
shared/
├── models/
│   ├── query.py             ← QueryRequest, QueryResponse
│   ├── company.py           ← Company, IntelligenceAgentConfig
│   └── audit.py             ← AuditLog entry
└── constants.py             ← K_ANONYMITY_THRESHOLD = 10, sensitivity tiers

```

### `packages/web/`

React dashboard — three-panel demo interface.

```
web/
├── src/
│   ├── components/
│   │   ├── QueryPanel.tsx        ← voice/text query input
│   │   ├── AgentActivityPanel.tsx ← live agent processing view
│   │   └── AuditPanel.tsx        ← real-time audit log + cost
│   ├── hooks/
│   │   ├── useQuery.ts           ← query submission + response
│   │   └── useAuditStream.ts     ← Supabase Realtime subscription
│   └── App.tsx
└── index.html

```

---

## Database Schema (Supabase)

### `companies`

```sql
id              uuid PRIMARY KEY
name            text NOT NULL
api_key_hash    text NOT NULL        -- queriers authenticate with this
created_at      timestamptz

```

### `intelligence_agents`

```sql
id              uuid PRIMARY KEY
company_id      uuid REFERENCES companies
config          jsonb                -- access rules, sensitivity tiers
active          boolean DEFAULT true
created_at      timestamptz

```

### `documents` (one table per company, partitioned by company_id)

```sql
id              uuid PRIMARY KEY
company_id      uuid REFERENCES companies
content         text
embedding       vector(768)          -- pgvector
metadata        jsonb                -- non-PII metadata only
created_at      timestamptz

```

### `queries`

```sql
id              uuid PRIMARY KEY
querier_api_key_hash  text
target_company_id     uuid REFERENCES companies
raw_query             text
structured_query      jsonb
response              text
blocked               boolean
block_reason          text
cost_usd              numeric(10,6)
record_count          int              -- for k-anonymity audit
created_at            timestamptz

```

### `audit_log`

```sql
id              uuid PRIMARY KEY
query_id        uuid REFERENCES queries
agent           text                 -- which agent logged this
event           text
payload         jsonb
created_at      timestamptz

```

---

## LangGraph State

```python
class QueryState(TypedDict):
    # Input
    query_id: str
    raw_query: str                   # original NL query
    querier_company_id: str

    # Router output
    structured_query: dict           # parsed intent + parameters
    target_agent_ids: list[str]      # which Intelligence Agents to hit

    # Intelligence Agent output
    raw_insights: list[dict]         # aggregated results (never rows)
    record_counts: list[int]         # for k-anonymity check

    # Privacy Guard output
    passed_privacy: bool
    block_reason: str | None
    sanitized_response: str

    # Pricing output
    cost_usd: float
    sensitivity_tier: str

    # Final
    response: str
    error: str | None

```

---

## Agent Flow (LangGraph Graph)

```python
graph = StateGraph(QueryState)

graph.add_node("router", query_router_node)
graph.add_node("intelligence", intelligence_agent_node)
graph.add_node("privacy_guard", privacy_guard_node)
graph.add_node("pricing", pricing_node)

graph.set_entry_point("router")

graph.add_edge("router", "intelligence")
graph.add_edge("intelligence", "privacy_guard")

graph.add_conditional_edges(
    "privacy_guard",
    lambda state: "pricing" if state["passed_privacy"] else "blocked",
    {
        "pricing": "pricing",
        "blocked": END
    }
)

graph.add_edge("pricing", END)

```

---

## Speechmatics Integration

Voice queries flow through Speechmatics real-time STT before entering the agent graph:

```
Microphone → Speechmatics WebSocket → transcript → POST /query (same flow)

```

The frontend opens a WebSocket to Speechmatics, streams audio, receives transcript chunks, and submits the final transcript as a normal text query. No changes needed in the agent graph.

---

## Gemini Usage


| Agent              | Model                     | Why                           |
| ------------------ | ------------------------- | ----------------------------- |
| Query Router       | Gemini 2.0 Flash          | Low latency NL parsing        |
| Intelligence Agent | Gemini 2.0 Flash          | RAG synthesis                 |
| Privacy Guard      | Featherless (open-source) | Domain-specialized compliance |


---

## Deployment (Vultr)

```
Vultr VM (Ubuntu 22.04)
└── Docker Compose
    ├── api          ← FastAPI on port 8000
    ├── web          ← React (served via nginx) on port 80
    └── worker       ← LangGraph agent worker

Supabase Cloud (external)
Gemini API (external)
Speechmatics API (external)
Featherless API (external)

```

Single `docker-compose.yml` at root handles everything. `.env` file with all secrets.

---

## Key Design Decisions

**Why LangGraph over vanilla Python?** The Privacy Guard must always be the last node. LangGraph's conditional edges enforce this structurally — it's impossible for a response to skip privacy validation. This is a correctness guarantee, not just a convention.

**Why pgvector over Pinecone/Qdrant?** Each company's data stays in the same Supabase instance, isolated by `company_id`. No data crosses into a third-party vector store. Keeps the "data never moves" guarantee credible.

**Why Featherless for Privacy Guard?** Featherless prize requires a domain-specialized open-source agent running async. The Privacy Guard is exactly that — it runs on every query, it's specialized in compliance logic, and it's fully reproducible from the repo.

**Why one demo company instead of real companies?** The demo has three seeded companies with realistic synthetic data. This makes the demo deterministic and impressive without requiring real enterprise customers.