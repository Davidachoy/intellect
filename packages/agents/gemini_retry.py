"""Exponential backoff for Gemini rate limits."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from loguru import logger

T = TypeVar("T")

_MAX_ATTEMPTS = 5
_INITIAL_DELAY_SEC = 1.0
_BACKOFF_FACTOR = 2.0


def _status_code(exc: BaseException) -> int | None:
    for attr in ("code", "status_code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    response = getattr(exc, "response", None)
    value = getattr(response, "status_code", None)
    return value if isinstance(value, int) else None


def _is_rate_limited(exc: BaseException) -> bool:
    if _status_code(exc) == 429:
        return True
    message = str(exc).lower()
    return (
        "429" in message
        or "rate limit" in message
        or "rate_limit" in message
        or "resource exhausted" in message
        or "resource_exhausted" in message
    )


async def with_gemini_retry(
    operation: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = _MAX_ATTEMPTS,
    initial_delay_sec: float = _INITIAL_DELAY_SEC,
) -> T:
    """Run an async Gemini SDK call with exponential backoff on 429/rate limits."""
    delay = initial_delay_sec
    last_exc: BaseException | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            return await operation()
        except BaseException as exc:
            last_exc = exc
            if not _is_rate_limited(exc) or attempt >= max_attempts:
                raise
            logger.warning(
                "Gemini rate limited (attempt {}/{}), retrying in {:.1f}s: {}",
                attempt,
                max_attempts,
                delay,
                exc,
            )
            await asyncio.sleep(delay)
            delay *= _BACKOFF_FACTOR

    assert last_exc is not None
    raise last_exc
