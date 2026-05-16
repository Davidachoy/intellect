"""GET /alerts — recent anomaly detection alerts."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel, Field

from db.client import get_supabase_client
from shared.models.anomaly import AnomalyAlert

router = APIRouter(tags=["alerts"])


class AlertsEnvelope(BaseModel):
    data: list[AnomalyAlert]
    meta: dict[str, Any] = Field(default_factory=dict)


@router.get("/alerts", response_model=AlertsEnvelope)
async def list_anomaly_alerts(
    limit: int = Query(default=20, ge=1, le=100),
    unacknowledged_only: bool = Query(default=True),
) -> AlertsEnvelope:
    try:
        client = await get_supabase_client()
        query = (
            client.table("anomaly_alerts")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
        )
        if unacknowledged_only:
            query = query.eq("acknowledged", False)
        result = await query.execute()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Alert storage unavailable",
        ) from exc
    except Exception as exc:
        logger.exception("Failed to list anomaly alerts")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load alerts",
        ) from exc

    alerts = [AnomalyAlert.model_validate(row) for row in (result.data or [])]
    return AlertsEnvelope(
        data=alerts,
        meta={"count": len(alerts), "unacknowledged_only": unacknowledged_only},
    )
