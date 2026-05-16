"""POST /ingest — data quality gate, embed and store company documents."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from data_quality.node import run_data_quality_gate
from fastapi import APIRouter, HTTPException, status
from intelligence.embeddings import embed_texts
from loguru import logger
from pydantic import BaseModel, Field
from shared.models.data_quality import DataQualityRecommendation

from db.client import get_supabase_client
from dependencies import IngestAuthenticatedCompanyDep
from ingest.pii import strip_pii_from_metadata
from shared.models.ingest import IngestRequest, IngestResponse

router = APIRouter(tags=["ingest"])

EMBED_BATCH_SIZE = 128
DB_INSERT_BATCH_SIZE = 100


class IngestMeta(BaseModel):
    company_id: str
    ingested_count: int = Field(..., ge=0)
    data_quality_score: int | None = None


class IngestEnvelope(BaseModel):
    data: IngestResponse
    meta: IngestMeta


async def _persist_ingest_audit(
    *,
    query_id: str,
    company_id: str,
    report_payload: dict[str, Any],
    event: str,
) -> None:
    client = await get_supabase_client()
    await client.table("queries").insert(
        {
            "id": query_id,
            "querier_api_key_hash": f"ingest:{company_id}",
            "target_company_id": company_id,
            "raw_query": "[INGEST] document batch",
            "structured_query": {"type": "ingest"},
            "response": None,
            "blocked": False,
        }
    ).execute()
    await client.table("audit_log").insert(
        {
            "query_id": query_id,
            "agent": "data_quality",
            "event": event,
            "payload": report_payload,
        }
    ).execute()


@router.post("/ingest", response_model=IngestEnvelope)
async def ingest_documents(
    body: IngestRequest,
    company: IngestAuthenticatedCompanyDep,
) -> IngestEnvelope:
    raw_docs = [
        {"content": doc.content, "metadata": doc.metadata} for doc in body.documents
    ]
    report = await run_data_quality_gate(raw_docs)
    ingest_query_id = str(uuid4())
    report_payload = report.model_dump(mode="json")

    if report.recommendation == DataQualityRecommendation.REJECT:
        await _persist_ingest_audit(
            query_id=ingest_query_id,
            company_id=str(company.company_id),
            report_payload=report_payload,
            event="rejected",
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Ingest rejected due to data quality score below threshold",
                "data_quality": report_payload,
            },
        )

    sanitized = [
        {
            "content": doc.content.strip(),
            "metadata": strip_pii_from_metadata(doc.metadata),
        }
        for doc in body.documents
    ]
    texts = [row["content"] for row in sanitized]

    try:
        vectors = await embed_texts(texts, batch_size=EMBED_BATCH_SIZE)
    except Exception as exc:
        logger.exception(
            "Embedding failed for company_id={} count={}",
            company.company_id,
            len(texts),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate embeddings",
        ) from exc

    if len(vectors) != len(sanitized):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Embedding count mismatch",
        )

    company_id_str = str(company.company_id)
    document_ids: list[str] = []
    rows: list[dict[str, object]] = []
    for item, vector in zip(sanitized, vectors, strict=True):
        doc_id = uuid4()
        document_ids.append(str(doc_id))
        rows.append(
            {
                "id": str(doc_id),
                "company_id": company_id_str,
                "content": item["content"],
                "embedding": vector,
                "metadata": item["metadata"],
            }
        )

    audit_event = (
        "warning"
        if report.recommendation == DataQualityRecommendation.REVIEW
        else "approved"
    )

    try:
        client = await get_supabase_client()
        for start in range(0, len(rows), DB_INSERT_BATCH_SIZE):
            chunk = rows[start : start + DB_INSERT_BATCH_SIZE]
            await client.table("documents").insert(chunk).execute()
        await _persist_ingest_audit(
            query_id=ingest_query_id,
            company_id=company_id_str,
            report_payload=report_payload,
            event=audit_event,
        )
    except RuntimeError as exc:
        logger.exception("Database unavailable for company_id={}", company.company_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document storage unavailable",
        ) from exc
    except Exception as exc:
        logger.exception("Failed to store documents for company_id={}", company.company_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist documents",
        ) from exc

    warning: str | None = None
    if report.recommendation == DataQualityRecommendation.REVIEW:
        warning = (
            f"Data quality score {report.score}/100 — review recommended before relying "
            "on this data for sensitive queries."
        )

    data = IngestResponse(
        company_id=UUID(company_id_str),
        document_ids=document_ids,
        ingested_count=len(document_ids),
        data_quality_score=report.score,
        data_quality_warning=warning,
    )
    return IngestEnvelope(
        data=data,
        meta=IngestMeta(
            company_id=company_id_str,
            ingested_count=data.ingested_count,
            data_quality_score=report.score,
        ),
    )
