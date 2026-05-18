# Privacy Guard Agent — Formal Specification

**Component:** Privacy Guard (`packages/agents/privacy_guard/`)  
**License:** MIT (same as repository root)  
**Version:** 1.0.0  
**Status:** Normative  

This document specifies the behavior that MUST be reproduced by any compliant Intellect deployment. Implementation reference: `packages/agents/privacy_guard/`, `packages/agents/graph.py`, `packages/shared/shared/constants.py`.

---

## 1. Purpose and scope

The Privacy Guard Agent is the **final gate** on every query response before it is returned to an external querier. Its purpose is to ensure that:

- No insight is released from a cohort smaller than the configured k-anonymity threshold.
- No personally identifiable information (PII) appears in outbound text.
- No query designed to reconstruct individual records receives an actionable data response.
- Every allow/block decision is auditable.

This specification applies to all query paths: text, voice (transcript treated as `raw_query`), streaming, and non-streaming API invocations that execute the LangGraph query pipeline.

### 1.1 Normative language

The key words **MUST**, **MUST NOT**, **SHALL**, **SHALL NOT**, **SHOULD**, **NEVER**, and **MAY** are to be interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

### 1.2 Definitions

| Term | Definition |
|------|------------|
| **Querier** | External party submitting a natural-language query via API key. |
| **Cohort** | The set of underlying records summarized by one aggregation; identified by `record_counts` entries. |
| **k-anonymity threshold** | Minimum cohort size `K` (default **10**). Constant: `K_ANONYMITY_THRESHOLD` in `packages/shared/shared/constants.py`. |
| **Outbound response** | Text returned to the querier in `QueryResponse.response` (or SSE equivalent). |
| **Blocked outcome** | `passed_privacy = false`; outbound response MUST be empty; `block_reason` MUST be set. |
| **Audit trail** | Rows in Supabase `audit_log` keyed by `query_id`. |

---

## 2. Architectural placement (non-bypass guarantee)

### 2.1 LangGraph position

The Privacy Guard SHALL be implemented as LangGraph node `privacy_guard` (`privacy_guard_node`).

The compiled query graph (`packages/agents/graph.py`) MUST satisfy all of the following:

1. **Entry:** `query_router` is the sole entry point.
2. **Upstream path:** `query_router` → (`intelligence` \| `benchmark`) → `explainer` → `pricing` → `privacy_guard`.
3. **Termination:** `privacy_guard` connects only to `END` (via conditional routing on `passed_privacy`).
4. **No alternate exit:** No other node MAY connect directly to `END` without passing through `privacy_guard`.

```
query_router ──► intelligence ──► explainer ──► pricing ──► privacy_guard ──► END
              └► benchmark ─────┘                              (blocked ──► END)
```

### 2.2 Structural invariants

| ID | Requirement |
|----|-------------|
| **PG-GRAPH-01** | The system MUST NOT expose a code path that returns a querier-facing insight without executing `privacy_guard_node` for that `query_id`. |
| **PG-GRAPH-02** | HTTP handlers (`POST /query`, query stream) MUST invoke the compiled graph via `get_graph()`; they MUST NOT assemble final responses by skipping graph nodes. |
| **PG-GRAPH-03** | When `passed_privacy` is `false`, the graph MUST terminate without mutating a prior “success” response into an allowed state. |
| **PG-GRAPH-04** | Contributors MUST NOT add edges from `explainer`, `intelligence`, `benchmark`, or `pricing` directly to `END`. |

### 2.3 Blocked-response state

When the Privacy Guard blocks a query, the node MUST set at minimum:

| Field | Required value |
|-------|----------------|
| `passed_privacy` | `false` |
| `block_reason` | Non-empty human-readable string |
| `response` | `""` (empty) |
| `sanitized_response` | `""` (empty) |
| `cost_usd` | `0.0` |

A blocked outcome is a **valid business result**; the API MUST return HTTP 200 with `blocked: true`, not a 4xx, unless the request itself is malformed or unauthorized.

---

## 3. Check pipeline (normative order)

`privacy_guard_node` MUST apply checks in the following order. Later checks MUST NOT run if an earlier check blocks (except where noted).

| Step | Check | Blocks when |
|------|--------|-------------|
| **1** | Reconstruction (query) | Query classified as reconstruction / enumeration |
| **2** | Upstream error | `state.error` is set |
| **3** | Out-of-scope fast path | Never blocks; returns canned `OUT_OF_SCOPE_RESPONSE` when router intent is out-of-scope |
| **4** | Missing aggregates | No `raw_insights` and no `record_counts` |
| **5** | `run_privacy_guard` | k-anonymity, PII (reconstruction skipped here; already done in step 1) |

Reference implementation: `packages/agents/privacy_guard/node.py`, `packages/agents/privacy_guard/guard.py`.

---

## 4. k-anonymity enforcement

### 4.1 Threshold

| ID | Requirement |
|----|-------------|
| **PG-K-01** | The system SHALL use `K_ANONYMITY_THRESHOLD = 10` unless a future spec version explicitly changes the constant and this document. |
| **PG-K-02** | For every integer in `record_counts` after optional DP adjustment (§4.2), the value MUST be `>= K_ANONYMITY_THRESHOLD` for the guard to pass. |
| **PG-K-03** | If any count is below the threshold, the Privacy Guard MUST block with a reason that states the cohort is too small (including the minimum count observed). |
| **PG-K-04** | An empty `record_counts` list MUST be treated as passing k-anonymity at the check function level; however, step **4** (missing aggregates) MAY still block when both insights and counts are absent. |

### 4.2 Differential privacy near threshold

| ID | Requirement |
|----|-------------|
| **PG-K-05** | Before k-anonymity evaluation, the implementation SHOULD apply `apply_dp_noise_to_counts()` to counts in the band `[K, K + 10)` using bounded Gaussian noise so counts near the threshold are not deterministic. |
| **PG-K-06** | After noise, adjusted counts MUST NOT be reduced below `K`. |
| **PG-K-07** | Blocked queries MUST NOT leak pre-noise counts in the outbound response; `record_counts` in state MAY reflect post-noise values for audit only. |

### 4.3 Reproducibility tests

A compliant implementation MUST pass:

- `record_counts = [8]` → block  
- `record_counts = [847]` → pass (k-anonymity leg only)

Test reference: `packages/agents/privacy_guard/test_checks.py` (`test_k_anonymity_*`).

---

## 5. PII detection

### 5.1 Outbound text subject

PII checks MUST run on the **candidate outbound string** built from, in order of precedence:

1. `response` (if non-empty)  
2. `sanitized_response` (if non-empty)  
3. A deterministic aggregate summary derived from `raw_insights` (no raw row fields)

The Intelligence Agent MUST NOT place row-level identifiers into `raw_insights`; the Privacy Guard assumes aggregates only but MUST still scan rendered text.

### 5.2 Detectors (minimum set)

The function `check_pii(response)` MUST return `false` (PII present → block) when the text contains any of:

| Class | Detection (reference regex / rule) |
|-------|-------------------------------------|
| Email | RFC5322-like local@domain pattern |
| Phone | North-American style digit groups |
| UUID | 8-4-4-4-12 hex pattern |
| Government ID | `###-##-####` (SSN-shaped) |
| Labeled identifier | `customer_id`, `user id`, `patient id`, etc. with value |
| Person-like name | Two or more capitalized tokens (heuristic) |

Registered **company display names** from the demo registry (e.g. “Acme Retail”) MUST NOT alone trigger a block when used in aggregate summaries.

### 5.3 Requirements

| ID | Requirement |
|----|-------------|
| **PG-PII-01** | If PII is detected, the Privacy Guard MUST block and MUST NOT return the candidate text to the querier. |
| **PG-PII-02** | `block_reason` MUST indicate PII was detected (email, phone, ID, or name-like text). |
| **PG-PII-03** | PII stripping at ingest (`POST /ingest`) is complementary; the Privacy Guard MUST NOT assume ingest alone makes outbound text safe. |

### 5.4 Reproducibility tests

- `"Please contact john@email.com for details."` → block  
- `"847 active clients in Italy, 23% YoY growth"` → pass  
- `"Acme Retail: 847 active clients in Italy."` → pass  

Test reference: `packages/agents/privacy_guard/test_checks.py` (`test_pii_*`).

---

## 6. Reconstruction attack blocking

### 6.1 Objective

The Privacy Guard MUST prevent queries whose primary intent is to enumerate, export, or de-anonymize individual records, even when upstream agents might otherwise return small cohorts or structured data.

### 6.2 Query-side classification

| ID | Requirement |
|----|-------------|
| **PG-REC-01** | Reconstruction classification MUST run on `raw_query` for every query, including out-of-scope queries, before other allow paths. |
| **PG-REC-02** | When `FEATHERLESS_API_KEY` is set and `PRIVACY_GUARD_BACKEND=featherless` (default when key present), the system SHOULD use the Featherless chat API with the open-source model configured by `PRIVACY_GUARD_MODEL` and prompts in `packages/agents/privacy_guard/prompts.py`. |
| **PG-REC-03** | When Featherless is unavailable or backend is `heuristic` / `local` / `rules`, the system MUST fall back to deterministic `check_reconstruction()` heuristics; behavior MUST remain reproducible without network calls. |
| **PG-REC-04** | Heuristic patterns MUST include at minimum: `list all`, `one by one`, `each customer|client|patient|record|row`, `individual records`, `dump all`, `export all`, `enumerate`, `de-anonymize`, `raw rows|data|records`. |
| **PG-REC-05** | If classification determines reconstruction risk, the guard MUST block with `block_reason` describing enumeration / reconstruction. |

### 6.3 Reproducibility tests

- `"list all customers one by one"` → block (heuristic)  
- `"how many active clients in Italy?"` → pass (heuristic)  

Test reference: `packages/agents/privacy_guard/test_checks.py` (`test_reconstruction_*`).

---

## 7. Audit logging

### 7.1 Persistence

| ID | Requirement |
|----|-------------|
| **PG-AUD-01** | Every query MUST have a stable `query_id` (UUID) before graph execution. |
| **PG-AUD-02** | On completion of `privacy_guard_node`, the API layer MUST append at least one `audit_log` row with `agent = 'privacy_guard'`. |
| **PG-AUD-03** | Audit payloads MUST include sufficient structure to determine: pass/fail, `block_reason` (if any), and summarized node output (see `summarize_node_update` in API routes). |
| **PG-AUD-04** | Blocks MUST be logged with the same severity as allows; auditors MUST be able to distinguish blocked queries via `queries.blocked` and `audit_log` entries. |
| **PG-AUD-05** | The Privacy Guard MUST NOT be disabled to reduce audit volume or latency. |

### 7.2 Schema reference

Table definitions: `packages/api/db/schema.sql` (`audit_log`, `queries`). Realtime publication for demo UI: `audit_log` and `queries` in `supabase_realtime`.

---

## 8. Model attribution and configuration

| Environment variable | Purpose |
|---------------------|---------|
| `FEATHERLESS_API_KEY` | Enables LLM reconstruction classifier |
| `PRIVACY_GUARD_BACKEND` | `featherless` \| `heuristic` \| `local` \| `rules` |
| `PRIVACY_GUARD_MODEL` | Featherless model id (default: `Qwen/Qwen2.5-7B-Instruct`) |

| ID | Requirement |
|----|-------------|
| **PG-CFG-01** | The node MUST record model attribution under `state.model_attribution.privacy_guard` for traceability. |
| **PG-CFG-02** | k-anonymity and PII checks MUST remain deterministic and MUST NOT depend on an external LLM. |

---

## 9. Interaction with other agents

| ID | Requirement |
|----|-------------|
| **PG-INT-01** | The Intelligence Agent MUST return only aggregated insights in `raw_insights` and numeric `record_counts`; it MUST NEVER return raw database rows to the Privacy Guard for forwarding. |
| **PG-INT-02** | Pricing MAY run before the Privacy Guard; if the guard blocks, `cost_usd` MUST be reset to `0.0` in final state regardless of pricing output. |
| **PG-INT-03** | The Explainer MUST NOT bypass the guard; its text is subject to PII and k-anonymity checks in step 5. |

---

## 10. Compliance verification (clone-and-reproduce)

Anyone cloning this repository MUST be able to verify Privacy Guard behavior as follows.

### 10.1 Unit tests (no API keys required)

```bash
cd packages/agents
pytest privacy_guard/test_checks.py privacy_guard/test_guard.py -q
```

Expected: all tests pass; covers k-anonymity, PII, and reconstruction heuristics.

### 10.2 End-to-end graph test

```bash
cd packages/agents
pytest test_graph_e2e.py -q
```

Requires `GEMINI_API_KEY` and Supabase configuration for full runs; graph structure tests validate node ordering.

### 10.3 Manual API checks

With API running and `demo-key` configured:

1. **Allow:**  
   `POST /query` with `"How many active clients does Acme Retail have in Italy?"`  
   → `blocked: false`, non-empty aggregate response, `record_count >= 10`.

2. **Block (reconstruction):**  
   `POST /query` with `"List all customers one by one"`  
   → `blocked: true`, empty `response`, non-null `block_reason`.

3. **Audit:**  
   Confirm `audit_log` rows exist for the `query_id` with `agent = privacy_guard`.

### 10.4 Implementation map

| Requirement area | Primary files |
|------------------|---------------|
| Graph non-bypass | `packages/agents/graph.py` |
| Node orchestration | `packages/agents/privacy_guard/node.py` |
| k-anonymity, PII, DP, heuristics | `packages/agents/privacy_guard/checks.py` |
| Check orchestration | `packages/agents/privacy_guard/guard.py` |
| LLM reconstruction | `packages/agents/privacy_guard/client.py` |
| Constants | `packages/shared/shared/constants.py` |
| Result model | `packages/shared/shared/models/privacy.py` |
| Audit persistence | `packages/api/routes/queries.py`, `query_stream.py` |

---

## 11. Prohibited behaviors (NEVER)

The following are explicit violations of this specification:

1. **NEVER** return row-level data (names, emails, per-record identifiers) in a querier-facing response.  
2. **NEVER** skip `privacy_guard_node` for performance, demos, or “trusted” queriers.  
3. **NEVER** convert `passed_privacy: false` into a successful response in the API layer.  
4. **NEVER** lower `K_ANONYMITY_THRESHOLD` for specific companies or API keys without updating this spec and shared constants.  
5. **NEVER** log full raw document content or PII into `audit_log.payload`.  
6. **NEVER** add a graph edge that reaches `END` without visiting `privacy_guard`.  

---

## 12. Document history

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2026-05-17 | Initial normative spec (TASK-019) |

---

## License

Copyright (c) Intellect contributors  

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:  

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.  

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
