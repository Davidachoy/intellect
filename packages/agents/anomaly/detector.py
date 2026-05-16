"""Background anomaly detector — reconstruction-style query bursts via audit_log."""

from __future__ import annotations

import asyncio
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from anomaly.alerts import create_anomaly_alert
from db.client import get_supabase_client
from loguru import logger
from shared.models.anomaly import AnomalyAlertCreate

_WINDOW = timedelta(minutes=2)
_SIMILARITY_THRESHOLD = 0.6
_BURST_COUNT = 5


def _normalize_query(text: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return {t for t in tokens if len(t) > 2}


def _queries_similar(a: str, b: str) -> bool:
    ta, tb = _normalize_query(a), _normalize_query(b)
    if not ta or not tb:
        return False
    intersection = len(ta & tb)
    union = len(ta | tb)
    return intersection / union >= _SIMILARITY_THRESHOLD


def _severity(count: int) -> str:
    if count >= 8:
        return "high"
    if count >= 6:
        return "medium"
    return "low"


@dataclass
class _QuerierWindow:
    events: list[tuple[datetime, str, UUID]] = field(default_factory=list)


class AnomalyDetector:
    """Tracks recent queries per querier for reconstruction bursts."""

    def __init__(self) -> None:
        self._windows: dict[str, _QuerierWindow] = defaultdict(_QuerierWindow)
        self._alerted: set[tuple[str, str]] = set()

    def _prune(self, querier_id: str, now: datetime) -> None:
        window = self._windows[querier_id]
        cutoff = now - _WINDOW
        window.events = [e for e in window.events if e[0] >= cutoff]

    async def on_query_observed(
        self,
        *,
        querier_id: str,
        raw_query: str,
        query_id: UUID,
    ) -> None:
        now = datetime.now(timezone.utc)
        self._prune(querier_id, now)
        self._windows[querier_id].events.append((now, raw_query, query_id))

        events = self._windows[querier_id].events
        if len(events) < _BURST_COUNT:
            return

        clusters: list[list[tuple[datetime, str, UUID]]] = []
        for _, query_text, qid in events:
            placed = False
            for cluster in clusters:
                if _queries_similar(query_text, cluster[0][1]):
                    cluster.append((now, query_text, qid))
                    placed = True
                    break
            if not placed:
                clusters.append([(now, query_text, qid)])

        for cluster in clusters:
            if len(cluster) < _BURST_COUNT:
                continue
            pattern_key = " ".join(sorted(_normalize_query(cluster[0][1])))
            dedupe_key = (querier_id, pattern_key)
            if dedupe_key in self._alerted:
                continue
            self._alerted.add(dedupe_key)

            query_ids = [item[2] for item in cluster]
            severity = _severity(len(cluster))
            alert = AnomalyAlertCreate(
                querier_id=querier_id,
                pattern="reconstruction_burst",
                query_ids=query_ids,
                severity=severity,  # type: ignore[arg-type]
            )
            alert_id = await create_anomaly_alert(alert)
            logger.warning(
                "anomaly: {} similar queries from querier={} severity={} alert_id={}",
                len(cluster),
                querier_id[:12],
                severity,
                alert_id,
            )


_detector = AnomalyDetector()


async def _load_query_for_audit_row(payload: dict[str, Any]) -> None:
    query_id = payload.get("query_id")
    if not query_id:
        return
    client = await get_supabase_client()
    result = (
        await client.table("queries")
        .select("id, raw_query, querier_api_key_hash")
        .eq("id", str(query_id))
        .limit(1)
        .execute()
    )
    if not result.data:
        return
    row = result.data[0]
    raw_query = str(row.get("raw_query") or "")
    if raw_query.startswith("[INGEST]"):
        return
    await _detector.on_query_observed(
        querier_id=str(row.get("querier_api_key_hash") or "unknown"),
        raw_query=raw_query,
        query_id=UUID(str(row["id"])),
    )


async def _poll_audit_log(since: datetime) -> datetime:
    client = await get_supabase_client()
    result = (
        await client.table("audit_log")
        .select("query_id, agent, event, created_at")
        .gte("created_at", since.isoformat())
        .eq("agent", "query_router")
        .eq("event", "routed")
        .order("created_at", desc=False)
        .execute()
    )
    latest = since
    for row in result.data or []:
        created = row.get("created_at")
        if created:
            latest = max(latest, datetime.fromisoformat(created.replace("Z", "+00:00")))
        await _load_query_for_audit_row(row)
    return latest


async def run_detector_forever(*, poll_interval_sec: float = 5.0) -> None:
    """Poll audit_log for new router events (Realtime-compatible deployment pattern)."""
    logger.info("anomaly detector: starting poll_interval={}s", poll_interval_sec)
    since = datetime.now(timezone.utc) - timedelta(seconds=30)
    while True:
        try:
            since = await _poll_audit_log(since)
        except Exception:
            logger.exception("anomaly detector: poll cycle failed")
        await asyncio.sleep(poll_interval_sec)


async def run_detector_realtime() -> None:
    """Subscribe to audit_log INSERTs via Supabase Realtime when available."""
    client = await get_supabase_client()

    def on_insert(payload: dict[str, Any]) -> None:
        record = payload.get("record") or payload.get("data", {}).get("record")
        if not record:
            return
        if record.get("agent") != "query_router" or record.get("event") != "routed":
            return
        asyncio.create_task(_load_query_for_audit_row(record))

    channel = client.channel("anomaly-audit-monitor")
    channel.on_postgres_changes(
        event="INSERT",
        schema="public",
        table="audit_log",
        callback=on_insert,
    )
    await channel.subscribe()
    logger.info("anomaly detector: subscribed to audit_log realtime")
    await asyncio.Event().wait()
