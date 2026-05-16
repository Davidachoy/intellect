"""Provider-agnostic LLM routing via LiteLLM (any model string, one code path)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from litellm import acompletion
from loguru import logger

from litellm_retry import with_litellm_retry
from query_router.llm_parse import parse_router_json
from query_router.models import LLMRouterOutput
from query_router.prompts import ROUTER_SYSTEM_PROMPT, ROUTER_USER_TEMPLATE

_JSON_SYSTEM_SUFFIX = (
    "\n\nRespond with a single JSON object only. "
    "No markdown fences, no commentary."
)


def _ensure_env_loaded() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    load_dotenv(repo_root / ".env", override=False)


def _user_prompt(raw_query: str) -> str:
    return ROUTER_USER_TEMPLATE.format(raw_query=raw_query.strip())


async def generate_llm_router_output(raw_query: str, *, model: str) -> LLMRouterOutput:
    """Call any LiteLLM-supported model; credentials come from standard env vars."""
    _ensure_env_loaded()
    logger.debug("LiteLLM router model={}", model)

    async def _call() -> object:
        return await acompletion(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": ROUTER_SYSTEM_PROMPT + _JSON_SYSTEM_SUFFIX,
                },
                {"role": "user", "content": _user_prompt(raw_query)},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )

    response = await with_litellm_retry(_call)
    text = response.choices[0].message.content
    if not text:
        raise ValueError(f"Model {model} returned empty router response")
    return parse_router_json(text)
