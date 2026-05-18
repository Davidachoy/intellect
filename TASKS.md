# Intellect — Task Backlog

> Each task is atomic. One agent, one task, one PR. Status: [ ] pending | [x] done | [~] in progress

---

## Phase 1 — Project Foundation

### TASK-001: Monorepo base setup [x]

**Agent:** Background Agent **Input:** Repo root is empty except for README, .gitignore, ARCHITECTURE.md, TASKS.md, core.mdc **Output:**

- `packages/api/` with `main.py`, `requirements.txt`, basic FastAPI app that returns `{"status": "ok"}` on GET `/health`
- `packages/agents/` with empty `__init__.py` and `state.py` containing `QueryState` TypedDict exactly as defined in ARCHITECTURE.md
- `packages/shared/` with `models/query.py`, `models/company.py`, `models/audit.py` containing Pydantic v2 models
- `packages/web/` with Vite + React + Tailwind scaffolded via `pnpm create vite`
- `docker-compose.yml` at root with services: `api`, `web`
- `.env.example` with all required env var keys (no values) **Verify:** `cd packages/api && uvicorn main:app` starts without errors

---

### TASK-002: Supabase schema [x]

**Agent:** Background Agent **Input:** ARCHITECTURE.md database schema section **Output:**

- `packages/api/db/schema.sql` with all tables: `companies`, `intelligence_agents`, `documents`, `queries`, `audit_log`
- `packages/api/db/seed.sql` with 3 demo companies and realistic synthetic data:
  - Company A: "Acme Retail" — 1000 synthetic customer records (age, region, segment, ltv — no PII)
  - Company B: "NordLogistics" — 500 synthetic shipment records (region, status, value)
  - Company C: "MedResearch" — 300 synthetic trial participant records (age_range, outcome, region)
- `packages/api/db/client.py` with async Supabase client using `supabase-py` **Verify:** Schema runs on Supabase without errors. Seed populates all three companies.

---

### TASK-003: Shared Pydantic models [x]

**Agent:** Background Agent **Input:** ARCHITECTURE.md models section **Output:** `packages/shared/models/` with:

```python
# query.py
class QueryRequest(BaseModel):
    raw_query: str
    querier_api_key: str

class QueryResponse(BaseModel):
    query_id: str
    response: str
    blocked: bool
    block_reason: str | None
    cost_usd: float
    sensitivity_tier: str

# company.py
class Company(BaseModel): ...
class IntelligenceAgentConfig(BaseModel): ...

# audit.py
class AuditEntry(BaseModel): ...

```

**Verify:** `from shared.models.query import QueryRequest` works from any package

---

## Phase 2 — Agent System

### TASK-004: LangGraph graph skeleton [x]

**Agent:** Background Agent **Input:** ARCHITECTURE.md agent flow section, `packages/agents/state.py` **Output:**

- `packages/agents/graph.py` with full LangGraph graph as defined in ARCHITECTURE.md
- All nodes stubbed — each node receives `QueryState` and returns it unmodified with a log entry
- Graph compiles and runs end-to-end with a test input without errors
- `packages/agents/run.py` with `async def run_query(query: str, company_id: str) -> QueryState` **Verify:** `python run.py` with input "how many customers in Italy?" runs all nodes and prints state

---

### TASK-005: Query Router Agent [x]

**Agent:** Background Agent **Input:** `packages/agents/graph.py`, Gemini API key in .env **Output:** `packages/agents/query_router/node.py` that:

- Receives `raw_query` from state
- Calls Gemini Flash with a structured prompt to extract: intent, filters, aggregation_type, target_domain
- Returns structured_query dict and populates `target_agent_ids` based on query domain
- Prompt lives in `packages/agents/query_router/prompts.py` **Example:**
- Input: "how many active clients does this company have in Italy?"
- Output structured_query: `{ "intent": "count", "filters": { "region": "Italy", "status": "active" }, "aggregation": "count", "domain": "customers" }` **Verify:** Unit test in `packages/agents/query_router/test_router.py` passes for 5 different query types

---

### TASK-006: Intelligence Agent — RAG core [x]

**Agent:** Background Agent **Input:** `packages/agents/state.py`, Supabase client, pgvector setup **Output:** `packages/agents/intelligence/` with:

- `base.py` — `IntelligenceAgent` class that takes `company_id` and `structured_query`
- `rag.py` — embeds query using Gemini Embedding, searches pgvector, aggregates results
- Returns `raw_insights: list[dict]` and `record_counts: list[int]` — NEVER raw rows
- Aggregation functions: count, average, percentage, group_by_region **Critical rule:** The SELECT query must always use GROUP BY or aggregate functions. Never SELECT * or SELECT individual records. **Verify:** Unit test queries Acme Retail's data and returns aggregated count, never individual rows

---

### TASK-007: Privacy Guard Agent [x]

**Agent:** Background Agent **Input:** `packages/agents/state.py`, `packages/shared/constants.py` (K_ANONYMITY_THRESHOLD = 10) **Output:** `packages/agents/privacy_guard/` with:

- `node.py` — Privacy Guard LangGraph node
- `checks.py` with these functions:
  - `check_k_anonymity(record_counts: list[int]) -> bool` — blocks if any count < 10
  - `check_pii(response: str) -> bool` — detects names, emails, IDs in response text
  - `check_reconstruction(query: str) -> bool` — detects queries trying to enumerate records
- Uses Featherless API for the LLM-based reconstruction check
- Sets `passed_privacy: bool` and `block_reason: str | None` in state **Verify:** Unit tests:
  - count of 8 → blocked (k-anonymity)
  - response containing "john@email.com" → blocked (PII)
  - "list all customers one by one" → blocked (reconstruction)
  - count of 847 → passes

---

### TASK-008: Pricing Agent [x]

**Agent:** Background Agent **Input:** `packages/agents/state.py` **Output:** `packages/agents/pricing/` with:

- `tiers.py` defining sensitivity tiers: 
  ```python
  TIERS = {    "public": 0.00,    "aggregated": 0.01,    "sensitive": 0.05,    "strategic": 0.25}

  ```
- `node.py` — calculates cost based on sensitivity_tier, logs to `queries` table **Verify:** Unit test confirms correct cost per tier

---

## Phase 3 — API Layer

### TASK-009: POST /query route [x]

**Agent:** Background Agent **Input:** `packages/api/main.py`, `packages/agents/run.py`, shared models **Output:** `packages/api/routes/queries.py` with:

- `POST /query` accepts `QueryRequest`
- Validates API key against `companies` table
- Calls `run_query()` from agents package
- Returns `QueryResponse`
- Logs full audit trail to `audit_log` table
- Returns blocked response (not 4xx) when privacy guard blocks — blocked is a valid business outcome **Verify:** `curl -X POST /query -d '{"raw_query": "how many clients in Italy", "querier_api_key": "demo-key"}'` returns valid QueryResponse

---

### TASK-010: POST /ingest route [x]

**Agent:** Background Agent **Input:** Supabase client, pgvector **Output:** `packages/api/routes/ingest.py` with:

- `POST /ingest` accepts company_id + list of documents (text + metadata)
- Strips PII from metadata before storing (email, name, phone fields removed)
- Generates embeddings via Gemini Embedding API
- Stores in `documents` table with pgvector embedding **Verify:** Ingest 10 documents, confirm they appear in Supabase with embeddings

---

### TASK-011: GET /audit/{query_id} route [ ]

**Agent:** Background Agent **Output:** `packages/api/routes/audit.py`

- Returns full audit trail for a query_id
- Shows each agent's decision + timing
- Used in the demo's audit panel **Verify:** After running a query, GET /audit/{id} returns all agent steps

---

## Phase 4 — Frontend Demo

### TASK-012: Three-panel demo layout [x]

**Agent:** Background Agent **Input:** `packages/web/src/` **Output:** Main demo layout with three panels side by side:

- **Left panel** `QueryPanel.tsx` — text input + voice button (Speechmatics)
- **Center panel** `AgentActivityPanel.tsx` — live agent processing steps with timing
- **Right panel** `AuditPanel.tsx` — real-time audit log + running cost counter
- Tailwind styling — dark theme, professional enterprise look
- Supabase Realtime subscription for live updates in center and right panels **Verify:** Layout renders correctly, three panels visible, no console errors

---

### TASK-013: Speechmatics voice input [x]

**Agent:** Background Agent **Input:** Speechmatics API key, `QueryPanel.tsx` **Output:**

- Voice button in QueryPanel opens Speechmatics WebSocket
- Real-time transcript appears as user speaks
- On silence/stop, transcript is submitted as query automatically
- Visual indicator: recording state (red pulse), processing state (spinner) **Verify:** Click voice button, speak "how many clients in Italy", transcript appears, query submits

---

### TASK-014: Agent activity live view [x]

**Agent:** Background Agent **Input:** `AgentActivityPanel.tsx`, audit_log Supabase Realtime **Output:**

- Subscribes to `audit_log` table via Supabase Realtime
- Each agent step appears as it completes: Router → Intelligence → Privacy Guard → Pricing
- Shows agent name, decision, timing in ms
- If Privacy Guard blocks: shows red "BLOCKED" with reason
- If passes: shows green "APPROVED" + final response **Verify:** Submit a query, watch all 4 agent steps appear in sequence in real time

---

### TASK-015: Audit panel + cost counter [x]

**Agent:** Background Agent **Input:** `AuditPanel.tsx`, queries table **Output:**

- Running total of queries processed + total cost accumulated
- Last 10 queries listed with: query text (truncated), response, cost, blocked status
- Cost counter animates when new query completes **Verify:** Run 3 queries, all appear in audit panel with correct costs

---

## Phase 5 — Demo Data & Polish

### TASK-016: Seed realistic demo data [x]

**Agent:** Background Agent **Output:** `packages/api/db/seed_vectors.py` that:

- Takes seed.sql data for all 3 companies
- Generates realistic text descriptions for each record
- Embeds all documents via Gemini Embedding API
- Inserts into pgvector store
- Run time < 2 minutes **Verify:** After seeding, query "how many customers in Italy" returns a real number > 10

---

### TASK-017: Docker Compose production config [x]

**Agent:** Background Agent **Output:** `docker-compose.yml` at repo root with:

- `api` service: FastAPI on port 8000, reads from .env
- `web` service: React built and served via nginx on port 80
- Health checks on both services
- `README.md` updated with: `docker-compose up` one-liner to run everything **Verify:** `docker-compose up` starts both services, demo accessible at localhost:80

---

## Phase 6 — Hackathon Submission

### TASK-018: README for judges [x]

**Agent:** Background Agent **Output:** `README.md` with:

- One-liner: "The data never moves. The intelligence does."
- What it does (3 sentences max)
- Architecture diagram (ASCII)
- How to run locally (5 steps max)
- How to run on Vultr (link to deploy guide)
- Tech stack badges
- Demo video link (placeholder until recorded) **Note:** Written for a judge who has 90 seconds to evaluate

---

### TASK-019: OpenSpec specs for Privacy Guard [x]

**Agent:** Background Agent **Output:** `openspec/specs/privacy-guard/spec.md` with formal requirements:

- SHALL enforce k-anonymity ≥ 10
- SHALL strip PII before any response
- SHALL block record reconstruction queries
- SHALL log every decision to audit_log
- SHALL never be bypassed in the agent graph **Verify:** Spec file exists and covers all Privacy Guard behaviors

---

## Demo Script (for video recording)

```
00:00 — Open demo. Three panels visible.
00:10 — "Today, companies can't monetize their data without selling it. 
         Until now."
00:20 — Click voice button. Say: 
         "How many active clients does Acme Retail have in Italy?"
00:30 — Watch center panel: Router → Intelligence → Privacy Guard → Pricing
00:40 — Response appears: "847 active clients, 23% YoY growth"
00:45 — Show audit panel: $0.05 charged. Raw data: never shown.
00:55 — Ask a blocked query: "List all customers one by one"
01:00 — Privacy Guard blocks it. Red BLOCKED appears.
01:10 — "The data never moved. The intelligence did."
01:15 — Show GitHub repo + architecture diagram.
01:30 — End.

```

