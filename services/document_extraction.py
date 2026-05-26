"""
document_extraction.py
----------------------
Responsible for reading a PDF resume file and extracting its raw text.

Input:  file path (str)
Output: plain text string (capped at 25,000 characters)
"""
import asyncio
import logging

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

_MAX_TEXT_CHARS = 25_000


async def extract_resume_text(file_path: str) -> str:
    """Open a PDF and return all page text concatenated, capped at 25,000 chars.

    The synchronous fitz calls run in a thread pool so the async event loop
    is never blocked.
    """
    def _extract() -> str:
        doc = fitz.open(file_path)
        text = "".join(page.get_text() for page in doc)
        doc.close()
        return text[:_MAX_TEXT_CHARS]

    return await asyncio.to_thread(_extract)
