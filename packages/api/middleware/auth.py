"""API key validation against the companies table."""

from __future__ import annotations

import hashlib
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from loguru import logger

from db.client import get_supabase_client


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


async def resolve_company_by_api_key(api_key: str) -> dict[str, Any]:
    """Look up a company by plaintext API key (hashed before query)."""
    key_hash = hash_api_key(api_key)

    try:
        client = await get_supabase_client()
    except RuntimeError as exc:
        logger.exception("Supabase client not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        ) from exc

    try:
        result = (
            await client.table("companies")
            .select("id, name, api_key_hash")
            .eq("api_key_hash", key_hash)
            .maybe_single()
            .execute()
        )
    except Exception as exc:
        logger.exception("Failed to validate API key")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        ) from exc

    if result is None or getattr(result, "data", None) is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    return result.data


class AuthenticatedCompany:
    """Resolved querier company from a valid API key."""

    def __init__(self, company_id: UUID, name: str, api_key_hash: str) -> None:
        self.company_id = company_id
        self.name = name
        self.api_key_hash = api_key_hash
