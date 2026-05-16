"""Exponential backoff for LiteLLM rate limits (e.g. Gemini 429)."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from loguru import logger

T = TypeVar("T")

_MAX_ATTEMPTS = 5
_INITIAL_DELAY_SEC = 1.0
_BACKOFF_FACTOR = 2.0


def _is_rate_limited(exc: BaseException) -> bool:
    try:
        from litellm.exceptions import RateLimitError

        if isinstance(exc, RateLimitError):
            return True
    except ImportError:
        pass

    message = str(exc).lower()
    return "429" in message or "rate limit" in message or "resource exhausted" in message


async def with_litellm_retry(
    operation: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = _MAX_ATTEMPTS,
    initial_delay_sec: float = _INITIAL_DELAY_SEC,
) -> T:
    """Run an async LiteLLM call with exponential backoff on 429 / rate limits."""
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
                "LiteLLM rate limited (attempt {}/{}), retrying in {:.1f}s: {}",
                attempt,
                max_attempts,
                delay,
                exc,
            )
            await asyncio.sleep(delay)
            delay *= _BACKOFF_FACTOR

    assert last_exc is not None
    raise last_exc
