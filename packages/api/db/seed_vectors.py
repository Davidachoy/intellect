"""TASK-016: Embed seed.sql documents into pgvector via Gemini.

Run from repo root (requires agents deps + .env):

    cd packages/agents && uv run python ../api/db/seed_vectors.py

Or with PYTHONPATH:

    PYTHONPATH=packages/agents:packages/shared:packages/api python packages/api/db/seed_vectors.py
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field

_REPO_ROOT = Path(__file__).resolve().parents[3]
_AGENTS_ROOT = _REPO_ROOT / "packages" / "agents"
_API_ROOT = _REPO_ROOT / "packages" / "api"
_SHARED_ROOT = _REPO_ROOT / "packages" / "shared"

for path in (str(_SHARED_ROOT), str(_API_ROOT), str(_AGENTS_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from db.client import close_supabase_client, get_supabase_client  # noqa: E402
from intelligence.embeddings import EMBEDDING_DIMENSIONS, embed_texts  # noqa: E402
from model_registry import configured_model_for_node, ensure_env_loaded  # noqa: E402

ACME_RETAIL_ID = "a0000000-0000-4000-8000-000000000001"
NORD_LOGISTICS_ID = "a0000000-0000-4000-8000-000000000002"
MED_RESEARCH_ID = "a0000000-0000-4000-8000-000000000003"

COMPANY_IDS = (ACME_RETAIL_ID, NORD_LOGISTICS_ID, MED_RESEARCH_ID)

EMBED_BATCH_SIZE = 128
DB_UPSERT_BATCH_SIZE = 100
FETCH_PAGE_SIZE = 1000
class DocumentRow(BaseModel):
    id: str
    company_id: str
    content: str


class SeedStats(BaseModel):
    company_id: str
    embedded: int = 0
    skipped: int = 0


class SeedReport(BaseModel):
    companies: list[SeedStats] = Field(default_factory=list)
    italy_active_count: int | None = None
    elapsed_sec: float = 0.0


async def _fetch_documents_without_embeddings(company_id: str) -> list[DocumentRow]:
    client = await get_supabase_client()
    rows: list[DocumentRow] = []
    offset = 0

    while True:
        end = offset + FETCH_PAGE_SIZE - 1
        response = (
            await client.table("documents")
            .select("id, company_id, content")
            .eq("company_id", company_id)
            .is_("embedding", "null")
            .order("id")
            .range(offset, end)
            .execute()
        )
        page = response.data or []
        if not page:
            break
        for item in page:
            rows.append(
                DocumentRow(
                    id=str(item["id"]),
                    company_id=str(item["company_id"]),
                    content=str(item["content"]),
                )
            )
        if len(page) < FETCH_PAGE_SIZE:
            break
        offset += FETCH_PAGE_SIZE

    return rows


async def _upsert_embeddings(rows: list[DocumentRow], vectors: list[list[float]]) -> None:
    if not rows:
        return

    client = await get_supabase_client()
    for start in range(0, len(rows), DB_UPSERT_BATCH_SIZE):
        chunk_rows = rows[start : start + DB_UPSERT_BATCH_SIZE]
        chunk_vectors = vectors[start : start + DB_UPSERT_BATCH_SIZE]
        payload = [
            {
                "id": doc.id,
                "company_id": doc.company_id,
                "content": doc.content,
                "embedding": vector,
            }
            for doc, vector in zip(chunk_rows, chunk_vectors, strict=True)
        ]
        await client.table("documents").upsert(payload).execute()


async def _embed_and_store(company_id: str) -> SeedStats:
    docs = await _fetch_documents_without_embeddings(company_id)
    stats = SeedStats(company_id=company_id)

    if not docs:
        logger.info("No documents pending embeddings company_id={}", company_id)
        return stats

    logger.info(
        "Embedding {} documents for company_id={}",
        len(docs),
        company_id,
    )

    texts = [d.content for d in docs]
    vectors = await embed_texts(texts, batch_size=EMBED_BATCH_SIZE)

    if len(vectors) != len(docs):
        raise RuntimeError(
            f"Embedding count mismatch: got {len(vectors)} for {len(docs)} documents"
        )

    await _upsert_embeddings(docs, vectors)
    stats.embedded = len(docs)
    return stats


async def _verify_italy_active_count() -> int:
    client = await get_supabase_client()
    response = await client.rpc(
        "intelligence_aggregate",
        {
            "p_company_id": ACME_RETAIL_ID,
            "p_aggregation": "count",
            "p_filters": {"region": "Italy", "status": "active"},
            "p_metric_field": "ltv_usd",
            "p_scope_ids": None,
        },
    ).execute()

    data: Any = response.data
    if isinstance(data, list):
        data = data[0] if data else {}
    return int((data or {}).get("record_count") or 0)


async def seed_vectors(*, verify: bool = True) -> SeedReport:
    ensure_env_loaded()
    model = configured_model_for_node("embeddings")
    logger.info(
        "Starting vector seed model={} dimensions={}",
        model,
        EMBEDDING_DIMENSIONS,
    )

    started = time.perf_counter()
    report = SeedReport()

    for company_id in COMPANY_IDS:
        report.companies.append(await _embed_and_store(company_id))

    if verify:
        report.italy_active_count = await _verify_italy_active_count()
        if report.italy_active_count <= 10:
            raise RuntimeError(
                f"Italy active count must be > 10 for demo k-anonymity; got {report.italy_active_count}"
            )

    report.elapsed_sec = time.perf_counter() - started
    total_embedded = sum(c.embedded for c in report.companies)
    logger.info(
        "Vector seed complete embedded={} elapsed_sec={:.1f} italy_active={}",
        total_embedded,
        report.elapsed_sec,
        report.italy_active_count,
    )
    return report


async def _main() -> None:
    parser = argparse.ArgumentParser(description="Embed demo documents (TASK-016)")
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip post-seed Italy active count check",
    )
    args = parser.parse_args()

    try:
        report = await seed_vectors(verify=not args.no_verify)
    finally:
        await close_supabase_client()

    if report.elapsed_sec > 120:
        logger.warning("Seed exceeded 2 minute target: {:.1f}s", report.elapsed_sec)

    print(
        f"embedded={sum(c.embedded for c in report.companies)} "
        f"elapsed_sec={report.elapsed_sec:.1f} "
        f"italy_active={report.italy_active_count}"
    )


if __name__ == "__main__":
    asyncio.run(_main())
