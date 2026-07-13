"""
smoke_test.py
=============
Quick local validation that the clause splitter and PDF extractor work
correctly WITHOUT needing an Anthropic API key.

Run with:
    cd backend
    .venv\Scripts\python smoke_test.py
"""

import sys
import os

# Add parent so we can import backend as a package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.clause_splitter import split_clauses
from backend.services.pdf_extractor import extract_text_from_pdf

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"

errors = 0

def check(label, condition):
    global errors
    if condition:
        print(f"  {PASS}  {label}")
    else:
        print(f"  {FAIL}  {label}  ← FAILED")
        errors += 1

# ── Clause Splitter ────────────────────────────────────────────────────────────
print("\n── Clause Splitter ──────────────────────────────────────────────────")

# Test 1: Numbered list
numbered = """1. The tenant shall pay rent of $1,200 on the first of each month.
2. Late payments incur a penalty of 10% per day.
3. The landlord may enter the premises with 24-hour notice."""
clauses = split_clauses(numbered)
check("Numbered list splits into 3 clauses", len(clauses) == 3)
check("First clause contains 'tenant'", "tenant" in clauses[0])

# Test 2: Article/Section headers
sectioned = """Section 1. Payment Terms
Rent is due on the 1st of every month.

Section 2. Termination
Either party may terminate with 30 days written notice."""
clauses = split_clauses(sectioned)
check("Section headers split into 2 clauses", len(clauses) == 2)

# Test 3: Blank-line paragraphs
paragraphs = """Rent of $1,200 is due monthly.

The tenant is responsible for all utilities.

Pets are not permitted on the premises."""
clauses = split_clauses(paragraphs)
check("Blank-line paragraphs split into 3 clauses", len(clauses) == 3)

# Test 4: Single clause fallback
single = "The tenant agrees to keep the property clean."
clauses = split_clauses(single)
check("Single sentence returns one clause", len(clauses) == 1)

# Test 5: Empty input
clauses = split_clauses("")
check("Empty input returns empty list", len(clauses) == 0)

# ── PDF Extractor ──────────────────────────────────────────────────────────────
print("\n── PDF Extractor ────────────────────────────────────────────────────")

# Test 6: Invalid bytes raise ValueError
try:
    extract_text_from_pdf(b"this is not a pdf")
    check("Invalid PDF raises ValueError", False)
except ValueError as e:
    check("Invalid PDF raises ValueError", True)
    check("Error message is user-friendly", "valid PDF" in str(e))

# Test 7: Empty bytes raise ValueError
try:
    extract_text_from_pdf(b"")
    check("Empty bytes raises ValueError", False)
except ValueError:
    check("Empty bytes raises ValueError", True)

# ── Summary ────────────────────────────────────────────────────────────────────
print(f"\n{'─' * 60}")
if errors == 0:
    print(f"  {PASS}  All tests passed.")
else:
    print(f"  {FAIL}  {errors} test(s) failed.")
    sys.exit(1)
