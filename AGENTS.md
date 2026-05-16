# AGENTS.md

## Cursor Cloud specific instructions

### Overview

Intellect is a monorepo with 4 packages: `packages/api` (FastAPI), `packages/agents` (LangGraph), `packages/shared` (Pydantic models), and `packages/web` (React/Vite). See `README.md` for full architecture.

### Running services

| Service | Command | Port | Notes |
|---|---|---|---|
| API | `cd packages/api && python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload` | 8000 | Health check: `GET /health` |
| Web | `cd packages/web && pnpm dev --host 0.0.0.0 --port 5173` | 5173 | Set `VITE_API_URL=http://localhost:8000` |

### Testing

- **API tests:** `python3 -m pytest packages/api/ingest/test_pii.py -v`
- **Agents tests:** `python3 -m pytest packages/agents/ -v` (58 tests, all pure-unit, no external dependencies needed)
- **Web lint:** `cd packages/web && pnpm lint` (pre-existing lint errors exist in `useQuerierAliases.ts` and `auditSteps.ts`)
- **Web typecheck:** `cd packages/web && pnpm exec tsc -b --noEmit`
- **Web build:** `cd packages/web && pnpm build`

### Environment variables

Copy `.env.example` to `.env`. The API and agent tests run without any secrets. For full end-to-end query flow, you need `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, and at least one LLM key (`OPENAI_API_KEY`). Set `ROUTER_MODE=heuristic` to bypass LLM requirements for the query router.

### Gotchas

- Use `python3` not `python` — only `python3` is on PATH in this environment.
- The `packages/agents` test suite uses `pytest-asyncio`; install it alongside `pytest`.
- The web package uses `pnpm` (lockfile: `pnpm-lock.yaml`). Use `pnpm install --frozen-lockfile`.
- The API's `monorepo_path.py` manipulates `sys.path` at startup to resolve cross-package imports; this runs automatically when `main.py` loads.
- Without Supabase configured, the `/query` endpoint returns 503 ("Authentication service unavailable") — this is expected. The `/health` endpoint works without any external services.
