"""Gemini-powered LLM routing."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

from gemini_client import generate_gemini_text
from gemini_retry import with_gemini_retry
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
    """Call Gemini Flash and parse the structured router JSON."""
    _ensure_env_loaded()
    logger.debug("Gemini router model={}", model)

    async def _call() -> str:
        return await generate_gemini_text(
            model=model,
            system_instruction=ROUTER_SYSTEM_PROMPT + _JSON_SYSTEM_SUFFIX,
            user_prompt=_user_prompt(raw_query),
            response_mime_type="application/json",
            temperature=0.1,
        )

    text = await with_gemini_retry(_call)
    if not text:
        raise ValueError(f"Model {model} returned empty router response")
    return parse_router_json(text)
