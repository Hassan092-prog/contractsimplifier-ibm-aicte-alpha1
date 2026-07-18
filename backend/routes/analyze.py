"""
backend/routes/analyze.py
==========================
FastAPI router for POST /api/analyze.

Request
-------
multipart/form-data with:
  - text (str, optional) : pasted contract text
  - file (UploadFile, optional) : PDF upload

At least one of text / file must be provided.

Response
--------
Server-Sent Events (SSE) stream of newline-delimited JSON chunks.
See README.md §API Reference for the full chunk schema.

Error handling
--------------
Each error condition is caught and streamed as an error chunk so the
frontend always receives well-formed SSE — it never sees a raw HTTP 500.
"""

import json
import logging
import os
from typing import AsyncIterator, Optional

import groq
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from ..models import ClauseResult, ErrorResult, SummaryResult
from ..services.clause_splitter import split_clauses
from ..services.claude_client import stream_analysis
from ..services.pdf_extractor import extract_text_from_pdf

logger = logging.getLogger(__name__)

router = APIRouter()

# Maximum allowed input length (characters). Overridable via env.
MAX_INPUT_CHARS = int(os.environ.get("MAX_INPUT_CHARS", 50_000))

# Maximum number of clauses we'll send to the LLM in one request.
MAX_CLAUSES = 50


# ---------------------------------------------------------------------------
# SSE helper
# ---------------------------------------------------------------------------

def _sse(data: dict) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(data)}\n\n"


# ---------------------------------------------------------------------------
# Core streaming generator
# ---------------------------------------------------------------------------

async def _analyze_stream(text: str) -> AsyncIterator[str]:
    """
    Generator that drives the full analysis pipeline and yields SSE strings.

    Steps
    -----
    1. Validate input length.
    2. Split into clauses.
    3. Stream Claude's response.
    4. Parse streaming text buffer into clause / summary JSON chunks.
    5. Yield each validated chunk as an SSE event.
    """

    # ── 1. Input validation ────────────────────────────────────────────────
    if len(text) > MAX_INPUT_CHARS:
        yield _sse(
            ErrorResult(
                message=(
                    f"Input is too long ({len(text):,} characters). "
                    f"Maximum allowed is {MAX_INPUT_CHARS:,} characters."
                )
            ).model_dump()
        )
        return

    # ── 2. Clause splitting ────────────────────────────────────────────────
    clauses = split_clauses(text)
    if not clauses:
        yield _sse(ErrorResult(message="No clauses found in the provided text.").model_dump())
        return

    if len(clauses) > MAX_CLAUSES:
        yield _sse(
            ErrorResult(
                message=(
                    f"Too many clauses detected ({len(clauses)}). "
                    f"Maximum is {MAX_CLAUSES}. Please split your contract into smaller sections."
                )
            ).model_dump()
        )
        return

    # ── 3 & 4. Stream + parse Claude output ───────────────────────────────
    buffer = ""
    in_summary = False  # True after we've seen the ===SUMMARY=== separator
    summary_buffer = ""

    try:
        async for chunk in stream_analysis(clauses):
            buffer += chunk

            # Process complete lines as they accumulate
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()

                if not line:
                    continue

                # Detect the summary separator
                if line == "===SUMMARY===":
                    in_summary = True
                    continue

                if in_summary:
                    summary_buffer += line
                    # Try to parse once we have what looks like a complete JSON object
                    if summary_buffer.endswith("}"):
                        try:
                            raw = json.loads(summary_buffer)
                            summary = SummaryResult(
                                verdict=raw.get("verdict", ""),
                                overall_risk=raw.get("overall_risk", "MEDIUM"),
                            )
                            yield _sse(summary.model_dump())
                        except (json.JSONDecodeError, KeyError, ValueError) as e:
                            logger.warning("Failed to parse summary JSON: %s | raw: %s", e, summary_buffer)
                            yield _sse(
                                ErrorResult(
                                    message="Model returned a malformed summary. Partial analysis above may still be useful."
                                ).model_dump()
                            )
                        summary_buffer = ""
                    continue

                # Try to parse a clause JSON line
                if line.startswith("{") and line.endswith("}"):
                    try:
                        raw = json.loads(line)
                        clause_result = ClauseResult(
                            index=raw.get("index", 0),
                            clause_text=raw.get("clause_text", ""),
                            explanation=raw.get("explanation", ""),
                            risk_level=raw.get("risk_level", "MEDIUM"),
                            reasoning=raw.get("reasoning", ""),
                        )
                        yield _sse(clause_result.model_dump())
                    except (json.JSONDecodeError, KeyError, ValueError) as e:
                        logger.warning("Failed to parse clause JSON: %s | line: %s", e, line)
                        # Skip malformed clause lines silently; they may be
                        # partial chunks that will complete in the next iteration.

        # ── Flush any remaining buffer content ──────────────────────────────
        # Handle case where model didn't end with a newline
        remainder = buffer.strip()
        if remainder and not in_summary:
            if remainder.startswith("{") and remainder.endswith("}"):
                try:
                    raw = json.loads(remainder)
                    if "verdict" in raw:
                        summary = SummaryResult(
                            verdict=raw.get("verdict", ""),
                            overall_risk=raw.get("overall_risk", "MEDIUM"),
                        )
                        yield _sse(summary.model_dump())
                    else:
                        clause_result = ClauseResult(
                            index=raw.get("index", 0),
                            clause_text=raw.get("clause_text", ""),
                            explanation=raw.get("explanation", ""),
                            risk_level=raw.get("risk_level", "MEDIUM"),
                            reasoning=raw.get("reasoning", ""),
                        )
                        yield _sse(clause_result.model_dump())
                except (json.JSONDecodeError, ValueError):
                    pass  # Genuinely unparseable remainder — discard

        # Flush summary buffer if separator was the last thing
        if in_summary and summary_buffer.strip():
            try:
                raw = json.loads(summary_buffer.strip())
                summary = SummaryResult(
                    verdict=raw.get("verdict", ""),
                    overall_risk=raw.get("overall_risk", "MEDIUM"),
                )
                yield _sse(summary.model_dump())
            except (json.JSONDecodeError, ValueError):
                pass

    except EnvironmentError as e:
        logger.error("Environment configuration error: %s", e)
        yield _sse(ErrorResult(message=str(e)).model_dump())

    except groq.AuthenticationError:
        logger.error("Groq authentication failed — check GROQ_API_KEY")
        yield _sse(
            ErrorResult(
                message="Authentication with the AI service failed. Please check your GROQ_API_KEY."
            ).model_dump()
        )

    except groq.RateLimitError:
        logger.warning("Groq rate limit hit")
        yield _sse(
            ErrorResult(
                message="The AI service is temporarily rate-limited. Please wait a moment and try again."
            ).model_dump()
        )

    except groq.APIStatusError as e:
        logger.error("Groq API error %s: %s", e.status_code, e.message)
        yield _sse(
            ErrorResult(
                message=f"AI service error (HTTP {e.status_code}). Please try again later."
            ).model_dump()
        )

    except Exception as e:
        logger.exception("Unexpected error during analysis")
        yield _sse(
            ErrorResult(message=f"An unexpected error occurred: {type(e).__name__}").model_dump()
        )


# ---------------------------------------------------------------------------
# Route definition
# ---------------------------------------------------------------------------

@router.post(
    "/analyze",
    summary="Analyze contract clauses",
    description=(
        "Accepts pasted contract text and/or a PDF upload. "
        "Returns a Server-Sent Events stream of per-clause analysis and an overall summary."
    ),
    response_description="SSE stream of JSON chunks (clause | summary | error)",
)
async def analyze(
    text: Optional[str] = Form(
        default=None,
        description="Pasted contract text. Required if no file is uploaded.",
    ),
    file: Optional[UploadFile] = File(
        default=None,
        description="PDF contract file. Required if no text is provided.",
    ),
) -> StreamingResponse:
    """POST /api/analyze — main analysis endpoint."""

    # ── Input validation ───────────────────────────────────────────────────
    if not text and not file:
        raise HTTPException(
            status_code=422,
            detail="You must provide either 'text' or 'file' (PDF).",
        )

    contract_text: str = ""

    # ── PDF extraction ─────────────────────────────────────────────────────
    if file:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=415,
                detail="Only PDF files are supported. Please upload a .pdf file.",
            )
        try:
            file_bytes = await file.read()
            contract_text = extract_text_from_pdf(file_bytes)
        except ValueError as e:
            # extract_text_from_pdf raises ValueError for user-facing errors
            # Stream it as an SSE error chunk rather than an HTTP error so the
            # frontend receives it consistently.
            async def _error_stream():
                yield _sse(ErrorResult(message=str(e)).model_dump())

            return StreamingResponse(
                _error_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no",
                },
            )

    # ── Merge pasted text with extracted PDF text if both provided ─────────
    if text:
        contract_text = (text.strip() + "\n\n" + contract_text).strip()

    contract_text = contract_text.strip()
    if not contract_text:
        raise HTTPException(
            status_code=422,
            detail="The provided input contains no readable text.",
        )

    # ── Stream response ────────────────────────────────────────────────────
    return StreamingResponse(
        _analyze_stream(contract_text),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable Nginx/proxy buffering
        },
    )
