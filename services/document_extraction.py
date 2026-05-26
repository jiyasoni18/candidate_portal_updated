"""
document_extraction.py
----------------------
Responsible for reading a PDF resume file and extracting its raw text.

Input:  file path (str)
Output: plain text string (capped at 25,000 characters)
"""
import asyncio
import logging
import urllib.request
import urllib.error

import fitz  # PyMuPDF
import docx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_MAX_TEXT_CHARS = 25_000


async def extract_resume_text(file_path: str) -> str:
    """Open a document (PDF or DOCX) and return all text concatenated, capped at 25,000 chars."""
    if file_path.lower().endswith('.docx'):
        return await extract_docx_text(file_path)
    return await extract_pdf_text(file_path)

async def extract_pdf_text(file_path: str) -> str:
    """Open a PDF and return all page text concatenated, capped at 25,000 chars."""
    def _extract() -> str:
        doc = fitz.open(file_path)
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
            for link in page.get_links():
                if "uri" in link:
                    text_parts.append(f"\n[URL found: {link['uri']}]")
        doc.close()
        text = "".join(text_parts)
        return text[:_MAX_TEXT_CHARS]
    return await asyncio.to_thread(_extract)

async def extract_docx_text(file_path: str) -> str:
    """Open a DOCX and return all text concatenated, capped at 25,000 chars."""
    def _extract() -> str:
        doc = docx.Document(file_path)
        text_parts = [paragraph.text for paragraph in doc.paragraphs]
        # Extract hyperlinks from rels
        try:
            for rel in doc.part.rels.values():
                if "hyperlink" in rel.reltype:
                    text_parts.append(f"\n[URL found: {rel._target}]")
        except Exception as e:
            logger.warning(f"Failed to extract docx links: {e}")
            
        text = "\n".join(text_parts)
        return text[:_MAX_TEXT_CHARS]
    return await asyncio.to_thread(_extract)

async def extract_url_text(url: str) -> str:
    """Fetch URL and extract visible text using BeautifulSoup, capped at 25,000 chars."""
    if not url.startswith('http://') and not url.startswith('https://'):
        url = 'https://' + url
        
    def _extract() -> str:
        try:
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            html = urllib.request.urlopen(req, timeout=10).read()
            soup = BeautifulSoup(html, 'html.parser')
            # Kill script and style elements
            for script in soup(["script", "style", "noscript", "header", "footer", "nav"]):
                script.decompose()
            text = soup.get_text(separator=' ', strip=True)
            return text[:_MAX_TEXT_CHARS]
        except Exception as e:
            logger.error("Failed to extract from URL %s: %s", url, e)
            raise ValueError(f"Failed to fetch or parse URL: {e}")
    return await asyncio.to_thread(_extract)
