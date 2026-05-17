# Intellect Agents

LangGraph pipeline: **router -> intelligence -> explainer -> pricing -> privacy_guard**.

## Model Backends

Intellect is intentionally limited to Gemini + Featherless:

| Node | Env var | Default model | Backend |
|------|---------|---------------|---------|
| **router** | `ROUTER_MODEL` | `gemini-3-flash-preview` | `google-genai` |
| **intelligence attribution** | `INTELLIGENCE_MODEL` | `gemini-3-flash-preview` | `google-genai` |
| **explainer** | `EXPLAINER_MODEL` | `gemini-3-flash-preview` | `google-genai` |
| **embeddings** (RAG) | `EMBEDDING_MODEL` | `gemini-embedding-2` | `google-genai` |
| **privacy_guard** | `PRIVACY_GUARD_MODEL` | `Qwen/Qwen2.5-7B-Instruct` | `featherless` |
| **voice_input** | `SPEECHMATICS_API_KEY` | `enhanced` | `speechmatics` |

### Gemini Mode

```env
GEMINI_API_KEY=your-key
ROUTER_MODE=auto
ROUTER_MODEL=gemini-3-flash-preview
EMBEDDING_MODEL=gemini-embedding-2
```

Privacy Guard uses Featherless when `FEATHERLESS_API_KEY` is set. Without that key,
the graph still enforces deterministic k-anonymity, PII, and reconstruction checks.

### Logs To Show Judges

Every node emits structured attribution:

```text
MODEL_ATTRIBUTION node=router provider=google model=gemini-3-flash-preview backend=google-genai used_gemini=true hackathon_tracks=[google_gemini]
HACKATHON_TRACK google_gemini node=router model=gemini-3-flash-preview
```

`POST /query` persists router attribution under `audit_log` -> `query_router` step -> `model_attribution`.

### Heuristic Test Mode

```env
ROUTER_MODE=heuristic
```

The router uses local rules for offline tests and demos without API calls.

## Run Locally

```bash
cd packages/agents
pip install -r requirements.txt
pip install -e ../shared

PYTHONPATH="../shared:." python run.py "how many clients in Italy?"
```

## Tests

```bash
PYTHONPATH="../shared:." pytest query_router/ -v
```
