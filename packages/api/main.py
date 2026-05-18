import os
from contextlib import asynccontextmanager

import monorepo_path

monorepo_path.setup_monorepo_paths()

from db.client import close_supabase_client
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from routes import audit, alerts, companies, ingest, queries, query_stream, speechmatics


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_supabase_client()


app = FastAPI(title="Intellect API", version="0.1.0", lifespan=lifespan)

_cors_origins = [
    o.strip()
    for o in os.environ.get(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if o.strip()
]
_cors_origin_regex = os.environ.get(
    "CORS_ORIGIN_REGEX",
    r"https?://[a-z0-9]+\.\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\.sslip\.io",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=_cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

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
