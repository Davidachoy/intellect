"""Short-lived Speechmatics JWT for browser real-time STT (API key stays server-side)."""

from __future__ import annotations

import os

import httpx
from fastapi import APIRouter, HTTPException, status
from loguru import logger

router = APIRouter(prefix="/speechmatics", tags=["speechmatics"])

MANAGEMENT_URL = "https://mp.speechmatics.com/v1/api_keys"


@router.get("/jwt")
async def get_realtime_jwt() -> dict[str, str]:
    """Mint a temporary real-time transcription key for the web client."""
    api_key = os.environ.get("SPEECHMATICS_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SPEECHMATICS_API_KEY is not configured",
        )

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                MANAGEMENT_URL,
                params={"type": "rt"},
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={"ttl": 60, "region": "eu"},
            )
    except httpx.HTTPError as exc:
        logger.error("Speechmatics JWT request failed: {}", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Speechmatics authentication service unavailable",
        ) from exc

    if response.status_code == 403:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Speechmatics API key unauthorized",
        )

    if response.status_code not in (200, 201):
        logger.warning(
            "Speechmatics JWT error status={} body={}",
            response.status_code,
            response.text[:500],
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create Speechmatics session token",
        )

    payload = response.json()
    key_value = payload.get("key_value")
    if not key_value:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid Speechmatics token response",
        )

    return {"jwt": key_value}
