from contextlib import asynccontextmanager

import monorepo_path

monorepo_path.setup_monorepo_paths()

from db.client import close_supabase_client
from fastapi import FastAPI
from routes import audit, companies, queries


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_supabase_client()


app = FastAPI(title="Intellect API", version="0.1.0", lifespan=lifespan)

app.include_router(queries.router)
app.include_router(companies.router)
app.include_router(audit.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
