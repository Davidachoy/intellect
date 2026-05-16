import os
from contextlib import asynccontextmanager

import monorepo_path

monorepo_path.setup_monorepo_paths()

from db.client import close_supabase_client
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import audit, alerts, companies, ingest, queries, query_stream, speechmatics


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_supabase_client()


app = FastAPI(title="Intellect API", version="0.1.0", lifespan=lifespan)

_cors_origins = os.environ.get(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(queries.router)
app.include_router(query_stream.router)
app.include_router(ingest.router)
app.include_router(companies.router)
app.include_router(audit.router)
app.include_router(alerts.router)
app.include_router(speechmatics.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
