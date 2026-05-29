"""
resume_parser.py
----------------
Pipeline 1 — takes raw resume text and asks the LLM to extract structured data.

Input:  raw text (str)
Output: ResumeParsedData (validated Pydantic model)
"""
import logging

from api.llm_client import call_openrouter
from schemas.resume import ResumeParsedData

logger = logging.getLogger(__name__)


def _build_prompt() -> str:  # exported for use by background_pipeline shim
    return (
        "You are a resume parsing engine. Extract structured data from the provided resume text.\n"
        "Return ONLY a valid JSON object with this exact structure — no markdown, no extra keys:\n"
        "{\n"
        '  "personal_info": {\n'
        '    "name": <string or null>,\n'
        '    "email": <string or null>,\n'
        '    "phone": <string or null>,\n'
        '    "linkedin": <string or null>,\n'
        '    "github": <string or null>,\n'
        '    "portfolio": <string or null>\n'
        "  },\n"
        '  "summary": <string or null>,\n'
        '  "skills": [<string>, ...],\n'
        '  "experience": [\n'
        '    {"title": <string or null>, "company": <string or null>, '
        '"duration": <string or null>, "description": <string or null>}\n'
        "  ],\n"
        '  "projects": [\n'
        '    {"name": <string or null>, "description": <string or null>, "link": <string or null>}\n'
        "  ],\n"
        '  "education": [\n'
        '    {"degree": <string or null>, "school": <string or null>, '
        '"year": <string or null>, "grade": <string or null>}\n'
        "  ],\n"
        '  "certifications": [<string>, ...]\n'
        "}\n"
        "Rules:\n"
        "- Use null for any missing string field.\n"
        "- Use an empty array [] for any missing list field.\n"
        "- Do not add extra keys beyond those listed above.\n"
        "- PRESERVE LINKS: If the text contains markdown links like [Link Text](URL), you MUST keep the exact markdown link in your string outputs (e.g. for certification names, project links/names, or descriptions).\n"
        "- Output must be valid JSON parseable without any pre-processing."
    )


async def parse_resume(raw_text: str) -> ResumeParsedData:
    """Send raw resume text to the LLM and return a validated ResumeParsedData object."""
    raw_json = await call_openrouter(_build_prompt(), raw_text, max_tokens=3000)
    return ResumeParsedData.model_validate_json(raw_json)
