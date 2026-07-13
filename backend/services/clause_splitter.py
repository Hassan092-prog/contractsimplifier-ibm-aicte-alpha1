"""
backend/services/clause_splitter.py
=====================================
Splits raw contract text into individual clauses using simple heuristics
(no ML). Supports:

  - Numbered lists  : "1.", "1)", "(1)", "Article 1.", "Section 1."
  - Lettered lists  : "a.", "a)", "(a)"
  - Double-newlines : blank-line separated paragraphs
  - Fallback        : treat the entire input as one clause

Strategy priority (in order):
  1. Numbered / lettered list detection (most reliable for formal contracts)
  2. Double-newline paragraph splitting
  3. Single clause fallback
"""

import re
from typing import List


# ── Regex patterns for list-style clause markers ──────────────────────────────

# Matches: "1.", "12.", "1)", "12)", "(1)", "(12)"
_NUMERIC_PATTERN = re.compile(
    r"(?m)^(?:\(?\d{1,3}[.)]\s+|\(\d{1,3}\)\s+)",
)

# Matches: "Article 1.", "Section 2.", "Clause 3."
_ARTICLE_PATTERN = re.compile(
    r"(?mi)^(?:article|section|clause|part|schedule)\s+\d+[\.:]\s*",
)

# Matches: "a.", "b)", "(c)" (single lower-case letter)
_ALPHA_PATTERN = re.compile(
    r"(?m)^(?:\([a-z]\)|[a-z][.)]\s+)",
)


def _split_by_pattern(text: str, pattern: re.Pattern) -> List[str]:
    """
    Generic splitter: finds all start positions of 'pattern' in text and
    returns the substrings between them as individual clauses.
    Returns an empty list if fewer than 2 matches are found (ambiguous).
    """
    matches = list(pattern.finditer(text))
    if len(matches) < 2:
        return []

    clauses: List[str] = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        clause = text[start:end].strip()
        if clause:
            clauses.append(clause)
    return clauses


def split_clauses(text: str) -> List[str]:
    """
    Main entry point.

    Parameters
    ----------
    text : str
        Raw contract text (already extracted from PDF or pasted by user).

    Returns
    -------
    List[str]
        Non-empty list of clause strings. Guaranteed to have at least one item.
    """
    text = text.strip()
    if not text:
        return []

    # 1. Try article / section headers first (most explicit)
    clauses = _split_by_pattern(text, _ARTICLE_PATTERN)
    if clauses:
        return clauses

    # 2. Try numeric list markers
    clauses = _split_by_pattern(text, _NUMERIC_PATTERN)
    if clauses:
        return clauses

    # 3. Try alphabetic list markers
    clauses = _split_by_pattern(text, _ALPHA_PATTERN)
    if clauses:
        return clauses

    # 4. Split on blank lines (paragraph mode)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paragraphs) > 1:
        return paragraphs

    # 5. Fallback — single clause
    return [text]
