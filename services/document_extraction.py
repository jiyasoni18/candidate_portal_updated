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
    """Open a PDF and return all page text concatenated with inline markdown links, capped at 25,000 chars."""
    def _extract() -> str:
        doc = fitz.open(file_path)
        text_parts = []
        for page in doc:
            links = page.get_links()
            words = page.get_text("words")  # list of (x0, y0, x1, y1, "word", block_no, line_no, word_no)
            
            # Sort words in reading order
            words.sort(key=lambda w: (w[5], w[6], w[7]))
            
            # Helper to check if a point is inside a rect
            def is_point_in_rect(px, py, rect):
                return rect[0] <= px <= rect[2] and rect[1] <= py <= rect[3]
                
            # Map each word to a link if it falls inside
            word_links = []
            for w in words:
                center_x = (w[0] + w[2]) / 2.0
                center_y = (w[1] + w[3]) / 2.0
                
                matched_uri = None
                for link in links:
                    rect = link.get("from")
                    if rect and is_point_in_rect(center_x, center_y, rect):
                        matched_uri = link.get("uri")
                        break
                word_links.append((w, matched_uri))
                
            # Group words by block/line and reconstruct text
            current_block = -1
            current_line = -1
            
            line_parts = []
            page_lines = []
            
            i = 0
            n = len(word_links)
            while i < n:
                w, uri = word_links[i]
                block_no = w[5]
                line_no = w[6]
                
                if block_no != current_block or line_no != current_line:
                    if line_parts:
                        page_lines.append(" ".join(line_parts))
                        line_parts = []
                    # If block changes, add an extra newline for block separation
                    if block_no != current_block and current_block != -1:
                        page_lines.append("")
                    current_block = block_no
                    current_line = line_no
                    
                if uri:
                    # Group all consecutive words sharing this exact link uri on the same line
                    link_words = [w[4]]
                    j = i + 1
                    while j < n:
                        next_w, next_uri = word_links[j]
                        if next_uri == uri and next_w[5] == block_no and next_w[6] == line_no:
                            link_words.append(next_w[4])
                            j += 1
                        else:
                            break
                    link_text = " ".join(link_words)
                    line_parts.append(f"[{link_text}]({uri})")
                    i = j  # advance
                else:
                    line_parts.append(w[4])
                    i += 1
                    
            if line_parts:
                page_lines.append(" ".join(line_parts))
                
            # Also keep a fallback list of any URLs at the end of the page to ensure they are never lost
            fallback_urls = []
            for link in links:
                if "uri" in link and link["uri"] not in fallback_urls:
                    fallback_urls.append(link["uri"])
            if fallback_urls:
                page_lines.append("")
                for furl in fallback_urls:
                    page_lines.append(f"[URL found: {furl}]")
                    
            text_parts.append("\n".join(page_lines))
            
        doc.close()
        text = "\n\n".join(text_parts)
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
