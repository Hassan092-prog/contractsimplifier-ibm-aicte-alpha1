"""
backend/services/claude_client.py
====================================
LLM client — now powered by Groq (free tier) instead of Anthropic.

Groq provides free access to top open-source models (Llama 3, Mixtral)
with very high rate limits and ultra-low latency inference.

Get a free API key at: https://console.groq.com

Responsibilities
----------------
- Build the messages list from the prompt template and clause list.
- Open a streaming connection to Groq using the AsyncGroq SDK.
- Yield raw text chunks as they arrive from the API.
- Translate Groq SDK errors into plain Python exceptions the route can catch.

NOTE: The Groq API key is read exclusively here via os.environ.
      It is never passed in from the frontend or stored in code.
"""

import os
from typing import AsyncIterator, List

from groq import AsyncGroq

from ..prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_client() -> AsyncGroq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY environment variable is not set. "
            "Get a free key at https://console.groq.com and add it to your .env file."
        )
    return AsyncGroq(api_key=api_key)


def _build_clauses_block(clauses: List[str]) -> str:
    """Format clause list into a numbered block for the user prompt."""
    lines = [f"{i + 1}. {clause}" for i, clause in enumerate(clauses)]
    return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# Main streaming function
# ---------------------------------------------------------------------------

async def stream_analysis(clauses: List[str]) -> AsyncIterator[str]:
    """
    Stream LLM analysis of the provided clauses via Groq.

    Yields
    ------
    str
        Raw text chunks from the Groq streaming API.
        The route layer is responsible for parsing these into JSON objects.

    Raises
    ------
    EnvironmentError
        If GROQ_API_KEY is not configured.
    groq.APIError
        On any Groq API-level failure (auth, rate limit, server error).
    """
    client = _get_client()

    # Default model: llama-3.3-70b-versatile (free, very capable, fast on Groq)
    # Override with GROQ_MODEL env var if needed.
    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

    user_message = USER_PROMPT_TEMPLATE.format(
        clauses_block=_build_clauses_block(clauses)
    )

    stream = await client.chat.completions.create(
        model=model,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
        stream=True,
    )

    async for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            yield content
