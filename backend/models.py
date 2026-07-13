"""
backend/models.py
=================
Pydantic models for request validation and response serialisation.
These are shared across routes and services so the contract (pun intended)
between layers is explicit and type-checked.
"""

from typing import Literal
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Response chunk models — mirrored in README API reference
# ---------------------------------------------------------------------------

class ClauseResult(BaseModel):
    """One analysed clause returned as an SSE chunk."""

    type: Literal["clause"] = "clause"
    index: int = Field(..., description="0-based position of the clause in the input")
    clause_text: str = Field(..., description="Verbatim clause text")
    explanation: str = Field(..., description="Plain-English explanation (≤2 sentences)")
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        ..., description="Risk rating for the signing party"
    )
    reasoning: str = Field(..., description="One-sentence rationale for the risk rating")


class SummaryResult(BaseModel):
    """Overall contract verdict — streamed as the final SSE chunk."""

    type: Literal["summary"] = "summary"
    verdict: str = Field(..., description="2-4 sentence plain-English overall summary")
    overall_risk: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        ..., description="Aggregate risk level across all clauses"
    )


class ErrorResult(BaseModel):
    """Error chunk — streamed when analysis cannot complete."""

    type: Literal["error"] = "error"
    message: str = Field(..., description="Human-readable error description")
