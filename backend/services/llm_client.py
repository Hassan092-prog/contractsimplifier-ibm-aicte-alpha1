"""
backend/services/llm_client.py
====================================
LLM client — powered primarily by Groq API (free tier) with Google Gemini API as fallback.

Primary: Groq API (`GROQ_API_KEY`) using AsyncGroq SDK.
Fallback: Google Gemini API (`GEMINI_API_KEY` or `GOOGLE_API_KEY`) using google-genai SDK.
"""

import logging
import os
from typing import AsyncIterator, List, Optional

from groq import AsyncGroq

try:
    from google import genai
    HAS_GEMINI_SDK = True
except ImportError:
    HAS_GEMINI_SDK = False

try:
    from ..prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
except (ImportError, ValueError):
    from prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


def _sanitize_key(key: Optional[str]) -> Optional[str]:
    """Return key if non-empty and not a placeholder, else None."""
    if not key:
        return None
    cleaned = key.strip()
    if not cleaned or cleaned.startswith("your_") or "placeholder" in cleaned.lower():
        return None
    return cleaned


def _build_clauses_block(clauses: List[str]) -> str:
    """Format clause list into a numbered block for the user prompt."""
    lines = [f"{i + 1}. {clause}" for i, clause in enumerate(clauses)]
    return "\n\n".join(lines)


async def _stream_groq(clauses: List[str], api_key: str) -> AsyncIterator[str]:
    client = AsyncGroq(api_key=api_key)
    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    user_message = USER_PROMPT_TEMPLATE.format(
        clauses_block=_build_clauses_block(clauses)
    )

    stream = await client.chat.completions.create(
        model=model,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        stream=True,
    )

    async for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            yield content


async def _stream_gemini(clauses: List[str], api_key: str) -> AsyncIterator[str]:
    if not HAS_GEMINI_SDK:
        raise ImportError("google-genai library is required for Gemini fallback.")

    client = genai.Client(api_key=api_key)
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    user_message = USER_PROMPT_TEMPLATE.format(
        clauses_block=_build_clauses_block(clauses)
    )
    full_prompt = f"{SYSTEM_PROMPT}\n\n{user_message}"

    response = await client.aio.models.generate_content_stream(
        model=model,
        contents=full_prompt,
    )

    async for chunk in response:
        if chunk.text:
            yield chunk.text


async def stream_analysis(clauses: List[str]) -> AsyncIterator[str]:
    """
    Stream LLM analysis of the provided clauses via Groq, falling back to Gemini API.

    Yields
    ------
    str
        Raw text chunks from the LLM streaming API.

    Raises
    ------
    EnvironmentError
        If neither GROQ_API_KEY nor GEMINI_API_KEY is configured with a valid key.
    RuntimeError
        If both primary and fallback APIs fail.
    """
    groq_api_key = _sanitize_key(os.environ.get("GROQ_API_KEY"))
    gemini_api_key = _sanitize_key(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))

    if not groq_api_key and not gemini_api_key:
        raise EnvironmentError(
            "Neither GROQ_API_KEY nor GEMINI_API_KEY is configured with a valid API key. "
            "Please add a real GROQ_API_KEY (from https://console.groq.com) or GEMINI_API_KEY (from https://aistudio.google.com) to your .env file."
        )

    # 1. Try Groq API as Primary if key is available
    if groq_api_key:
        logger.info("Attempting primary LLM analysis with Groq API...")
        groq_failed = False
        try:
            chunks_yielded = 0
            async for chunk in _stream_groq(clauses, groq_api_key):
                chunks_yielded += 1
                yield chunk
            if chunks_yielded > 0:
                return
        except Exception as e:
            logger.warning("Groq API failed: %s. Checking for Gemini fallback...", e)
            groq_failed = True

        if not groq_failed:
            return

    # 2. Try Gemini API as Fallback if Groq was unavailable or failed
    if gemini_api_key:
        logger.info("Attempting fallback LLM analysis with Google Gemini API...")
        try:
            async for chunk in _stream_gemini(clauses, gemini_api_key):
                yield chunk
            return
        except Exception as e:
            logger.error("Gemini API fallback failed: %s", e)
            raise RuntimeError(f"Primary Groq and fallback Gemini both failed. Details: {e}") from e

    raise EnvironmentError(
        "Groq API call failed and no valid GEMINI_API_KEY fallback is configured."
    )
