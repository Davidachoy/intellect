"""Persist anomaly alerts to Supabase."""

from __future__ import annotations

from uuid import UUID

from db.client import get_supabase_client
from loguru import logger
from shared.models.anomaly import AnomalyAlertCreate


async def create_anomaly_alert(alert: AnomalyAlertCreate) -> UUID | None:
    client = await get_supabase_client()
    row = {
        "querier_id": alert.querier_id,
        "pattern": alert.pattern,
        "query_ids": [str(q) for q in alert.query_ids],
        "severity": alert.severity,
    }
    try:
        result = await client.table("anomaly_alerts").insert(row).execute()
        if result.data:
            return UUID(str(result.data[0]["id"]))
    except Exception:
        logger.exception("Failed to create anomaly alert pattern={}", alert.pattern)
    return None
