# Intellect Agents

LangGraph pipeline: **router → intelligence → pricing → privacy_guard**.

## Google Gemini track (AI Agent Olympics)

Intellect targets the **Best use of Gemini** prize. Gemini is used where NL reasoning and embeddings matter; other sponsors use their own backends.

| Node | Env var | Default model | Hackathon track |
|------|---------|---------------|-----------------|
| **router** | `ROUTER_MODEL` | `gemini/gemini-2.0-flash` | `google_gemini` |
| **intelligence** | `INTELLIGENCE_MODEL` | `gemini/gemini-2.0-flash` | `google_gemini` |
| **embeddings** (RAG) | `EMBEDDING_MODEL` | `gemini/gemini-embedding-001` | `google_gemini` |
| **privacy_guard** | `PRIVACY_GUARD_MODEL` | Featherless catalog | `featherless` |
| **voice_input** | Speechmatics API | — | `speechmatics` |

### Hackathon demo mode

Pin Gemini defaults without removing LiteLLM for local dev:

```env
HACKATHON_GOOGLE_TRACK=true
GEMINI_API_KEY=your-key
ROUTER_MODEL=gemini/gemini-2.0-flash
```

### Logs to show judges

Every node emits structured logs:

```
MODEL_ATTRIBUTION node=router provider=google model=gemini/gemini-2.0-flash backend=litellm used_gemini=true hackathon_tracks=[google_gemini]
HACKATHON_TRACK google_gemini node=router model=gemini/gemini-2.0-flash
```

`POST /query` persists router attribution under `audit_log` → `query_router` step → `model_attribution`.

### Modo pruebas (ahora)

Sin gastar créditos ni llamar APIs:

```env
ROUTER_MODE=heuristic
```

El router usa reglas locales (Italy, clients, NordLogistics, etc.). La demo API (`847 clients…`) sigue funcionando.

### Probar con LLM real (OpenAI / Claude)

```env
ROUTER_MODE=auto
ROUTER_MODEL=gpt-4o-mini
ROUTER_MODEL_FALLBACKS=claude-3-5-haiku-latest
OPENAI_API_KEY=sk-...
```

### Modo demo hackathon (Gemini)

Solo cuando grabes el video o envíes a jueces:

```env
ROUTER_MODE=auto
ROUTER_MODEL=gemini/gemini-2.0-flash
HACKATHON_GOOGLE_TRACK=true
GEMINI_API_KEY=...
```

## Run locally

```bash
cd packages/agents
pip install -r requirements.txt
pip install -e ../shared

# API-style run + attribution summary
PYTHONPATH="../shared:." python run.py "how many clients in Italy?"

# Full LangGraph
PYTHONPATH="../shared:." python run.py --graph "how many clients in Italy?"
```

## Tests

```bash
PYTHONPATH="../shared:." pytest query_router/ -v
```
