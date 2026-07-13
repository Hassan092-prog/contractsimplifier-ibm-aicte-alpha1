"""
backend/services/pdf_extractor.py
====================================
Extracts plain text from an uploaded PDF file using pypdf.

Error handling strategy
-----------------------
- Returns extracted text on success.
- Raises ValueError with a user-friendly message if:
    * The uploaded file is not a valid PDF.
    * The PDF contains no extractable text (e.g. scanned image-only PDF).
  We do NOT fail silently — the error propagates to the route which converts
  it into an SSE error chunk so the frontend can display a clear message.
"""

import io
from typing import IO

try:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "pypdf is required for PDF extraction. "
        "Install it with: pip install pypdf"
    ) from exc


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract all text from a PDF supplied as raw bytes.

    Parameters
    ----------
    file_bytes : bytes
        Raw bytes of the uploaded PDF file.

    Returns
    -------
    str
        Concatenated text from all pages, separated by double newlines.

    Raises
    ------
    ValueError
        If the file is not a valid PDF or contains no extractable text.
    """
    if not file_bytes:
        raise ValueError("Uploaded file is empty.")

    try:
        reader = PdfReader(io.BytesIO(file_bytes))
    except PdfReadError as exc:
        raise ValueError(
            "The uploaded file does not appear to be a valid PDF. "
            "Please check the file and try again."
        ) from exc
    except Exception as exc:
        raise ValueError(
            f"Failed to open the PDF file: {exc}"
        ) from exc

    pages_text: list[str] = []
    for page_num, page in enumerate(reader.pages, start=1):
        try:
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages_text.append(page_text.strip())
        except Exception:
            # Skip unreadable pages rather than failing the whole document
            continue

    if not pages_text:
        raise ValueError(
            "Could not extract text from the uploaded PDF. "
            "The file may be a scanned image-only document. "
            "Please use a PDF with selectable text, or paste the contract text directly."
        )

    return "\n\n".join(pages_text)
