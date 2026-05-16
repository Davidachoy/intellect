"""Async Supabase client for agent packages."""

from __future__ import annotations

import os
from typing import Optional

from loguru import logger
from supabase import AsyncClient, acreate_client

_client: Optional[AsyncClient] = None


async def get_supabase_client() -> AsyncClient:
    global _client

    if _client is not None:
        return _client

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in the environment"
        )

    _client = await acreate_client(url, key)
    logger.debug("Agents Supabase async client initialized")
    return _client


async def close_supabase_client() -> None:
    global _client
    _client = None
    logger.debug("Agents Supabase async client closed")
