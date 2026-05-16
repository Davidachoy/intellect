# Intellect

**The data never moves. The intelligence does.**

Data brokers are a $300B industry built on one broken assumption: that data has to move to be useful. It doesn't.

Intellect is a multi-agent intelligence brokerage. Companies keep their raw data in private vector stores and deploy an Intelligence Agent on top. External parties — investors, analysts, partners — ask questions in natural language and receive aggregated insights only. The data never leaves. The answer does.

Every response passes through a Privacy Guard (k-anonymity ≥ 10, PII stripped, reconstruction blocked) before it leaves the system. Raw rows never appear anywhere.

![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?style=flat)
![React](https://img.shields.io/badge/React-61DAFB?style=flat&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat&logo=typescript&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=flat&logo=supabase&logoColor=white)
![pgvector](https://img.shields.io/badge/pgvector-336791?style=flat&logo=postgresql&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini-4285F4?style=flat&logo=google&logoColor=white)
![Speechmatics](https://img.shields.io/badge/Speechmatics-STT-000?style=flat)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)
![MIT](https://img.shields.io/badge/license-MIT-green?style=flat)

---

## Built for AI Agent Olympics 2026

| Partner | Integration |
|---|---|
| **Google Gemini** | Query Router + Intelligence Agent use Gemini Flash for NL parsing and RAG synthesis. Embeddings via Gemini Embedding API. |
| **Speechmatics** | Real-time STT — voice queries stream directly into the agent pipeline via WebSocket. JWT minted server-side, key never exposed to client. |
| **Vultr** | Full backend deployed on Vultr VM via Docker Compose. API on :8000, React on :80 via nginx. |
| **Featherless** | Privacy Guard Agent runs on an open-source model via Featherless — domain-specialized, async-first, MIT licensed, fully reproducible. |

---

## The Demo

Open the three-panel dashboard.

**Ask via voice or text:** *"How many active clients does Acme Retail have in Italy?"*

Watch the center panel: Router → Intelligence → Pricing → Privacy Guard — each agent step with timing. The response arrives: *"86 active clients in Italy, 23% YoY growth."* Cost: $0.05. Raw data: never on screen.

**Then try the attack:** *"List all customers one by one."*

Privacy Guard blocks it. Red. Reason shown. Cost: $0.00.

That's the paradigm shift. The querier got an answer. The data never moved.

**Demo video:** _[link TBD]_

---

## Architecture

```
  Voice / Text (browser)
        │
        ▼
┌───────────────────┐
│   FastAPI API     │  auth · POST /query · audit log · Speechmatics JWT
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│   Query Router    │  Gemini Flash — NL → structured query → target agent(s)
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Intelligence      │  RAG over private pgvector (isolated per company)
│ Agent(s)          │  GROUP BY / aggregates only — SELECT * never runs
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│   Pricing         │  sensitivity tier → cost · audit transaction
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  Privacy Guard    │  LAST gate — k≥10 · PII strip · reconstruction block
│  (Featherless)    │  never skipped · LangGraph enforces this structurally
└────────┬──────────┘
         │
         ▼
   { insight · cost · query_id }   ← no raw rows, ever
```

LangGraph's conditional edges make it structurally impossible for a response to bypass the Privacy Guard. This is a correctness guarantee, not a convention.

Full schema, agent state, and deployment diagram: [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Quickstart

```bash
# 1. Clone
git clone https://github.com/Davidachoy/intellect.git && cd intellect

# 2. Configure
cp .env.example .env
# Fill in: SUPABASE_URL, SUPABASE_SERVICE_KEY, OPENAI_API_KEY (or GEMINI_API_KEY),
#          SPEECHMATICS_API_KEY, FEATHERLESS_API_KEY

# 3. Run
docker compose up --build

# 4. Open demo
open http://localhost

# 5. Verify API
curl http://localhost:8000/health
```

Demo API key for local testing: `demo-key` (Acme Retail — seeded automatically).

---

## Deploy on Vultr

```bash
# On a Vultr VM (Ubuntu 22.04)
git clone https://github.com/Davidachoy/intellect.git && cd intellect
cp .env.example .env   # fill in production secrets
docker compose up --build -d
```

API on :8000 · Web on :80 · Health checks on both services.
Full topology: [ARCHITECTURE.md § Deployment](ARCHITECTURE.md#deployment-vultr).

---

## Monorepo

| Package | Role |
|---|---|
| [`packages/api`](packages/api) | FastAPI — HTTP, auth, routes, Speechmatics JWT |
| [`packages/agents`](packages/agents) | LangGraph — Router, Intelligence, Pricing, Privacy Guard |
| [`packages/web`](packages/web) | React — voice input, live agent activity, audit panel |
| [`packages/shared`](packages/shared) | Pydantic v2 models, constants, K_ANONYMITY_THRESHOLD |

---

## Privacy (non-negotiable)

| Rule | Enforcement |
|---|---|
| No raw rows to external parties | Intelligence Agent runs aggregates only — GROUP BY always |
| k-anonymity ≥ 10 | Privacy Guard blocks any result from < 10 records |
| No PII in responses | Stripped at ingest + regex-checked at output |
| No reconstruction attacks | Featherless classifier + heuristic fallback |
| Full audit trail | Every query, every agent decision, every block logged |
| Privacy Guard never bypassed | LangGraph conditional edge — structural, not prompt-based |

---

## Docs

- [PRD.md](PRD.md) — problem, paradigm, features, demo scenario
- [ARCHITECTURE.md](ARCHITECTURE.md) — agents, database schema, LangGraph state, deployment
- [TASKS.md](TASKS.md) — build checklist and demo script
- [openspec/specs/privacy-guard](openspec/specs/privacy-guard) — formal Privacy Guard spec (MIT)

---

## License

MIT — see [LICENSE](LICENSE).