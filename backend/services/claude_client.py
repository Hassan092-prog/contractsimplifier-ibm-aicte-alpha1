"""
backend/services/claude_client.py
====================================
Thin wrapper around the Anthropic Python SDK.

Responsibilities
----------------
- Build the messages list from the prompt template and clause list.
- Open a streaming connection to Claude using the SDK's streaming context manager.
- Yield raw text chunks as they arrive from the API.
- Translate Anthropic SDK errors into plain Python exceptions the route can catch.

NOTE: The Anthropic API key is read exclusively here via os.environ.
      It is never passed in from the frontend or stored in code.
"""

import json
import os
from typing import AsyncIterator, List

import anthropic

from ..prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE


# ---------------------------------------------------------------------------
# Module-level client — instantiated once, reused across requests.
# The SDK reads ANTHROPIC_API_KEY from the environment automatically.
# ---------------------------------------------------------------------------

def _get_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY environment variable is not set. "
            "Copy .env.example to .env and add your key."
        )
    return anthropic.Anthropic(api_key=api_key)


def _build_clauses_block(clauses: List[str]) -> str:
    """Format clause list into a numbered block for the user prompt."""
    lines = [f"{i + 1}. {clause}" for i, clause in enumerate(clauses)]
    return "\n\n".join(lines)


async def stream_analysis(clauses: List[str]) -> AsyncIterator[str]:
    """
    Stream Claude's analysis of the provided clauses.

    Yields
    ------
    str
        Raw text chunks from the Claude streaming API.
        The route layer is responsible for parsing these into JSON objects.

    Raises
    ------
    EnvironmentError
        If ANTHROPIC_API_KEY is not configured.
    anthropic.APIError
        On any Anthropic API-level failure (auth, rate limit, server error).
    """
    client = _get_client()
    model = os.environ.get("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")

    user_message = USER_PROMPT_TEMPLATE.format(
        clauses_block=_build_clauses_block(clauses)
    )

    # Use the synchronous streaming API wrapped for async yielding.
    # anthropic.Anthropic is synchronous; for true async use AsyncAnthropic.
    # We use AsyncAnthropic here for non-blocking SSE delivery.
    async_client = anthropic.AsyncAnthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY")
    )

    async with async_client.messages.stream(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        async for text_chunk in stream.text_stream:
            yield text_chunk
