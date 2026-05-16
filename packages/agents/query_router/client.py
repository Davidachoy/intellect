import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from loguru import logger

from query_router.models import LLMRouterOutput
from query_router.prompts import ROUTER_SYSTEM_PROMPT, ROUTER_USER_TEMPLATE

GEMINI_MODEL = "gemini-2.0-flash"


def _ensure_env_loaded() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    load_dotenv(repo_root / ".env", override=False)


@lru_cache(maxsize=1)
def get_gemini_client() -> genai.Client:
    _ensure_env_loaded()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set")
    return genai.Client(api_key=api_key)


async def generate_router_output(raw_query: str) -> LLMRouterOutput:
    client = get_gemini_client()
    user_prompt = ROUTER_USER_TEMPLATE.format(raw_query=raw_query.strip())

    logger.debug("Calling Gemini router model={}", GEMINI_MODEL)
    response = await client.aio.models.generate_content(
        model=GEMINI_MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=ROUTER_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_json_schema=LLMRouterOutput.model_json_schema(),
            temperature=0.1,
        ),
    )

    text = response.text
    if not text:
        raise ValueError("Gemini returned empty router response")

    return LLMRouterOutput.model_validate_json(text)
