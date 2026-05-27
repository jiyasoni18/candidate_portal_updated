"""
Enhanced Resume Analyzer Service

Wraps the analyzer.py functions and integrates with the existing pipeline.
Provides enhanced analysis with ATS scoring, gap detection, and PDF generation.
"""
import json
import re
from typing import Dict, Any, List, Optional
from io import BytesIO

from config import settings
from api.llm_client import call_openrouter


# Model constants — fall back to the configured default so invalid model names
# don't silently break LLM calls.
MODEL_ANALYSIS = "google/gemini-2.0-flash-001"
MODEL_REFINE = settings.OPENROUTER_MODEL
MODEL_PDF = settings.OPENROUTER_MODEL


async def _call_llm_async(model: str, messages: list, temperature: float = 0.2, max_tokens: int = 2000) -> str:
    """
    Async wrapper for LLM calls using the project's llm_client.
    Separates system and user messages correctly.
    """
    system_prompt = ""
    user_content = ""

    for msg in messages:
        role = msg.get("role", "")
        if role == "system":
            system_prompt = msg["content"]
        elif role == "user":
            user_content = msg["content"]

    # call_openrouter always sends system + user; pass empty string for system
    # when the prompt is entirely user-side (as is the case for enhanced analysis)
    response = await call_openrouter(system_prompt, user_content, model)
    return response


def _strip_markdown_json(text: str) -> str:
    """Remove ```json ... ``` fences if present."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


async def analyze_ats_score(
    resume_text: str,
    jd_text: str,
    model_name: str = MODEL_ANALYSIS,
) -> Dict[str, Any]:
    """
    ATS-focused analysis: scores how well the resume is optimised for ATS
    parsing and keyword matching against the JD.

    Returns:
      ats_score, ats_explanation, improvements, core_strengths, summary
    """
    from datetime import date as _date

    today_str = _date.today().strftime("%B %Y")

    prompt = f"""You are an expert Applicant Tracking System (ATS) evaluator.
The current date is {today_str}.

Your job is to simulate how a real ATS parser would score this resume against this specific Job Description (JD).

════════════════════════════════════════════════════════
STEP 1 — EXTRACT JD REQUIREMENTS (do this first, internally)
════════════════════════════════════════════════════════
Read the JD carefully and extract:
A) REQUIRED KEYWORDS: Every skill, tool, technology, methodology, or qualification the JD explicitly lists as required. Use the EXACT wording from the JD.
B) PREFERRED/NICE-TO-HAVE KEYWORDS: Any skills listed as "preferred", "nice to have", or "exposure to".
C) JOB TITLE KEYWORD: The exact job title in the JD (e.g., "Data Scientist").
D) REQUIRED SECTIONS: Standard resume sections expected by ATS (e.g., Professional Summary, Technical Skills, Education, Experience/Projects).

════════════════════════════════════════════════════════
STEP 2 — SCORE THE RESUME (4 components, sum = 100)
════════════════════════════════════════════════════════

COMPONENT 1 — REQUIRED KEYWORD MATCH (50 points max):
For each required keyword from Step 1A, check if the resume contains it (or a close synonym that an ATS would accept).
- Exact match = 1 point per keyword
- Close synonym match = 0.5 points per keyword
- Not found = 0 points
Score = (total points earned / total required keywords) × 50
Round to nearest integer.

COMPONENT 2 — PREFERRED KEYWORD MATCH (15 points max):
Same as Component 1 but for Step 1B preferred keywords.
Score = (matched preferred keywords / total preferred keywords) × 15

COMPONENT 3 — JOB TITLE / ROLE ALIGNMENT (15 points max):
- Job title appears verbatim in resume (Professional Summary or headline) → 15 points
- Job title is partially present or closely mentioned → 8 points
- Not present at all → 0 points

COMPONENT 4 — RESUME STRUCTURE & ATS PARSABILITY (20 points max):
Award points for each of the following present and properly formatted:
- Professional Summary section present → 5 points
- Technical Skills section with categorized skills → 5 points
- Education section with degree and institution → 4 points
- Experience or Projects section with bullet-point achievements → 4 points
- Contact information (email, phone, or links) → 2 points

ats_score = Component1 + Component2 + Component3 + Component4 (max 100)

════════════════════════════════════════════════════════
STEP 3 — GENERATE OUTPUT
════════════════════════════════════════════════════════

Return ONLY a valid JSON object with these exact keys:

- "ats_score": Integer 0-100. Computed from Step 2.
- "ats_explanation": 2-3 sentences. State the score breakdown (e.g., "Keyword match: X/50, Job title: Y/15, Structure: Z/20") and what specifically is causing points to be lost. Use EXACT JD wording.
- "improvements": List of strings — STRICTLY ONLY terminology/wording mismatches. Where the candidate HAS the skill but uses different words than the JD uses, causing ATS keyword miss.
  FORMAT: "Resume uses '[resume wording]' — JD requires '[exact JD term]'. Rephrase to '[exact JD term]' to improve keyword match."
  DO NOT put missing skills here. If no wording mismatches exist, return []. List ALL terminology mismatches; do not limit the number.
- "core_strengths": List of 3-5 strings — candidate's strongest JD-aligned qualifications. Use the exact JD terminology where possible.
- "summary": 2-3 sentence overview of suitability for this specific role.

STRICT RULES:
- All output MUST use the exact terminology from the JD, not generic descriptions.
- "improvements" = ONLY cases where skill EXISTS in resume but uses WRONG words vs JD. Never use this for missing skills.
- DO NOT INCLUDE EXACT MATCHES in improvements. If the resume already uses the exact JD term (e.g. "Linear Regression" -> "Linear Regression"), it is NOT an improvement. DO NOT INCLUDE IT.
- DO NOT MAP UNRELATED CONCEPTS in improvements (e.g. do not map "workflow automation" to "Learning & Development"). Only map actual synonymous terms.
- Do NOT invent metrics or fabricate evidence.
- Output valid JSON only. No markdown fences.

════════════════════════════════════════════════════════
JOB DESCRIPTION:
{jd_text}

RESUME:
{resume_text}
════════════════════════════════════════════════════════
"""
    messages = [{"role": "user", "content": prompt}]
    result_text = await _call_llm_async(model_name, messages, temperature=0.0, max_tokens=1500)
    result_text = _strip_markdown_json(result_text)
    return json.loads(result_text)


async def analyze_jd_match(
    resume_text: str,
    jd_text: str,
    model_name: str = MODEL_ANALYSIS,
    # Scoring weights — sum to 90; remaining 10 is AI Holistic
    w_exp: int = 20,
    w_core: int = 30,
    w_gth: int = 15,
    w_cons: int = 15,
    w_edu: int = 10,
    min_years: float = 0,
    jd_title_skill: str = "",
    job_title: str = "",
    jd_summary: str = "",
    mandatory_skills: str = "",
    good_to_have_skills: str = "",
) -> Dict[str, Any]:
    """
    Structured JD match scoring using the RANKING_PROMPT.

    Returns the full JSON dict:
      score, dropped, flags, section_scores, section_reasons,
      mandatory_skills_check, good_to_have_check, strengths, gaps, summary
    """
    from datetime import date as _date
    from rank_resume import RANKING_PROMPT

    today = _date.today()
    today_date_str = today.strftime("%m/%Y")

    _job_title = job_title or "Not specified"
    _jd_summary = jd_summary or (jd_text[:300] + "..." if len(jd_text) > 300 else jd_text)
    _mandatory_skills = mandatory_skills or "Derive from the full JD text above."
    _good_to_have_skills = good_to_have_skills or "Derive from the full JD text above."
    _jd_title_skill = jd_title_skill or "Derive the primary skill from the job title above."

    prompt = RANKING_PROMPT.format(
        today_date=today_date_str,
        today_month=today.month,
        today_year=today.year,
        W_EXP=w_exp,
        W_CORE=w_core,
        W_GTH=w_gth,
        W_CONS=w_cons,
        W_EDU=w_edu,
        MIN_YEARS=min_years,
        JD_TITLE_SKILL=_jd_title_skill,
        job_title=_job_title,
        jd_summary=_jd_summary,
        full_jd_text=jd_text,
        mandatory_skills=_mandatory_skills,
        good_to_have_skills=_good_to_have_skills,
        resume_data=resume_text,
    )

    messages = [{"role": "user", "content": prompt}]
    result_text = await _call_llm_async(model_name, messages, temperature=0.0, max_tokens=4000)
    result_text = _strip_markdown_json(result_text)
    return json.loads(result_text)

import hashlib
import collections

# LRU Cache for analyses to prevent memory leak in production
MAX_CACHE_SIZE = 100
_analysis_cache = collections.OrderedDict()

# Keep backward-compat alias — orchestrator currently calls this name
async def analyze_resume_enhanced(
    resume_text: str,
    jd_text: str,
    api_key: Optional[str] = None,
    model_name: str = MODEL_ANALYSIS,
) -> Dict[str, Any]:
    """
    Runs both ATS scoring and JD match scoring, merges results into one dict.

    The merged dict contains:
      From ATS:   ats_score, ats_explanation, improvements, core_strengths, summary
      From Match: score (match_score), section_scores, section_reasons,
                  mandatory_skills_check, good_to_have_check, gaps, flags
    """
    # Use a deterministic hash cache for exact same inputs to prevent score fluctuation
    cache_key = hashlib.sha256(f"{resume_text.strip()}|{jd_text.strip()}|{model_name}".encode('utf-8')).hexdigest()
    if cache_key in _analysis_cache:
        import copy
        _analysis_cache.move_to_end(cache_key) # Mark as most recently used
        return copy.deepcopy(_analysis_cache[cache_key])

    import asyncio

    ats_result, match_result = await asyncio.gather(
        analyze_ats_score(resume_text, jd_text, model_name),
        analyze_jd_match(resume_text, jd_text, model_name),
        return_exceptions=True,
    )

    merged: Dict[str, Any] = {}

    if isinstance(ats_result, Exception):
        merged["ats_score"] = None
        merged["ats_explanation"] = "ATS analysis unavailable."
        merged["improvements"] = []
        merged["core_strengths"] = []
        merged["summary"] = ""
    else:
        merged.update(ats_result)

    if isinstance(match_result, Exception):
        merged["match_score"] = None
        merged["gaps"] = []
        merged["section_scores"] = {}
        merged["section_reasons"] = {}
        merged["mandatory_skills_check"] = []
        merged["good_to_have_check"] = []
        merged["strengths"] = merged.get("core_strengths", [])
        merged["flags"] = {}
    else:
        # Expose the ranking score as match_score for UI consistency
        merged["match_score"] = match_result.get("score")
        merged["gaps"] = match_result.get("gaps", [])
        merged["section_scores"] = match_result.get("section_scores", {})
        merged["section_reasons"] = match_result.get("section_reasons", {})
        merged["mandatory_skills_check"] = match_result.get("mandatory_skills_check", [])
        merged["good_to_have_check"] = match_result.get("good_to_have_check", [])
        merged["strengths"] = match_result.get("strengths", merged.get("core_strengths", []))
        merged["flags"] = match_result.get("flags", {})
        merged["dropped"] = match_result.get("dropped", False)

    import copy
    _analysis_cache[cache_key] = copy.deepcopy(merged)
    # Evict oldest if we exceed capacity
    if len(_analysis_cache) > MAX_CACHE_SIZE:
        _analysis_cache.popitem(last=False)

    return merged


def parse_custom_additions(custom_text: str) -> Dict[str, List[str]]:
    """
    Parse custom additions into categorized sections.
    
    Recognises lines like "certificate: <text>", "education: <text>".
    Returns a dict with keys 'certificates', 'education', 'additional' containing lists of strings.
    
    Args:
        custom_text: Free-form text with optional prefixed sections
        
    Returns:
        Dict with categorized additions
    """
    sections = {"certificates": [], "education": [], "additional": []}
    if not custom_text:
        return sections
    
    lines = [line.strip() for line in re.split(r"[\n,]", custom_text) if line.strip()]
    for line in lines:
        lower = line.lower()
        if lower.startswith("certificate:") or lower.startswith("certificates:"):
            content = line.split(":", 1)[1].strip()
            if content:
                sections["certificates"].append(content)
        elif lower.startswith("education:"):
            content = line.split(":", 1)[1].strip()
            if content:
                sections["education"].append(content)
        else:
            sections["additional"].append(line)
    
    return sections


async def refine_custom_additions(
    gaps_data: Dict[str, Dict[str, str]],
    custom_text: str,
    jd_text: str,
    api_key: Optional[str] = None,
    model_name: str = MODEL_REFINE
) -> Dict[str, Any]:
    """
    Refine gap content and custom additions in a single API call.
    
    Args:
        gaps_data: Dict mapping index -> {"gap": str, "note": str}
        custom_text: User-provided custom additions
        jd_text: Job description text
        api_key: Optional API key (uses config if not provided)
        model_name: LLM model to use for refinement
        
    Returns:
        Dict with "gaps" (refined gap paragraphs) and "custom" (refined custom additions)
    """
    if not gaps_data and not custom_text.strip():
        return {"gaps": {}, "custom": ""}
    
    gaps_text = "\n".join(
        [f"ID {idx} | Gap: '{data['gap']}' | User Notes: '{data['note']}'"
         for idx, data in gaps_data.items()]
    ) if gaps_data else "None"
    
    prompt = f"""You are an expert resume writer and career coach.

You will receive three inputs:
1. The target Job Description (JD).
2. A list of resume gaps with user-provided notes for each.
3. Optional custom additions the user wants to include in their resume.

Your tasks:
A) For each gap:
   - If the user notes start with "GENERATE_PROJECT:", DO NOT write a standard gap paragraph. Instead, generate a full, realistic ATS-friendly project (title and 2 bullet points) demonstrating that skill. You MUST start the output string with exactly "project: " (e.g., "project: Basic AI Pipeline - Developed a robust data pipeline...").
   - Otherwise, transform the user notes into a concise, professional, ATS-friendly paragraph addressing that gap (MAXIMUM 2-3 sentences). Make sure the phrasing, keywords, and tone align strongly with the target Job Description. Be specific - use action verbs, but STRICTLY DO NOT invent, hallucinate, or mention any numerical metrics, numbers, or percentages (e.g., 15%, 20%, 3x) unless they are explicitly provided by the user in their notes.
B) If custom additions are provided, rewrite them as polished, ATS-friendly resume content. IF the user prefixed an addition with a specific section (e.g., "certificate: ...", "education: ..."), YOU MUST PRESERVE THAT PREFIX in your rewritten output. For certificates, output the exact name of the certificate, the agency, and the score if provided; DO NOT add extra words like "Completed " before it, and DO NOT use any bold formatting (**). DO NOT merge distinct sections into a single paragraph; keep them separated by newlines if necessary. DO NOT invent or hallucinate metrics or numbers.
C) HYPERLINKS & URLS: If the user's notes or custom additions contain any URLs or hyperlinks, you MUST preserve them exactly as provided in your refined output. Do not strip, shorten, or alter any URL.
D) ABOUT ME / PROFESSIONAL SUMMARY: If any custom addition line is prefixed with "about me:" or "professional summary:" (case-insensitive), treat that content as the professional summary material. Make slight professional modifications to it if needed to align with the JD, but DO NOT differentiate it from a professional summary. Preserve the "about me:" prefix in your output so the PDF generator can merge it into the Professional Summary section.
E) PROJECTS: If a custom addition is prefixed with "project:" (case-insensitive), you MUST format it as a new Project and place it in the Projects section, DO NOT put it in the Professional Summary.
{{
  "gaps": {{
    "0": "Refined ATS-friendly paragraph for gap ID 0",
    "1": "Refined ATS-friendly paragraph for gap ID 1"
  }},
  "custom": "Polished custom additions paragraph (empty string if none)"
}}
Do not include markdown fencing. Do not include any commentary outside the JSON.

--- Gap Notes ---
{gaps_text}

--- Custom Additions ---
{custom_text if custom_text.strip() else "None"}

--- Target Job Description ---
{jd_text}
"""
    
    messages = [{"role": "user", "content": prompt}]
    content_str = await _call_llm_async(model_name, messages, temperature=0.2, max_tokens=2000)
    content_str = _strip_markdown_json(content_str)
    return json.loads(content_str)


async def generate_ats_pdf(
    resume_text: str,
    accepted_texts: str,
    improvements_text: str,
    custom_text: str,
    jd_text: str,
    template_name: str = "Classic ATS",
    api_key: Optional[str] = None,
    model_name: str = MODEL_PDF
) -> BytesIO:
    """
    Generate an ATS-optimized PDF resume using the enhanced analysis results.
    
    Args:
        resume_text: Original resume text
        accepted_texts: Refined gap content to integrate
        improvements_text: Terminology improvements to apply
        custom_text: Custom additions from user
        jd_text: Job description text
        template_name: PDF template to use ("Classic ATS", "Modern Accent", "Two-Column Professional")
        api_key: Optional API key (uses config if not provided)
        model_name: LLM model to use for PDF generation
        
    Returns:
        BytesIO buffer containing the generated PDF
    """
    # Import here to avoid issues if reportlab is not installed
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, ListFlowable,
            ListItem, HRFlowable, Table, TableStyle, KeepInFrame
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
    except ImportError:
        raise ImportError(
            "reportlab is required for PDF generation. Install with: pip install reportlab"
        )
    
    if "Two-Column" in template_name:
        page_limit_rule = (
            "6. STRICT PAGE LIMIT (MAXIMUM 1 A4 PAGE): While you must fit the content on "
            "one page, DO NOT arbitrarily delete or minimize the candidate's core Projects "
            "or Professional Experience. Preserve the full length, depth, and original content of their technical projects and work experience exactly as they are."
        )
    else:
        page_limit_rule = (
            "6. Ensure the final resume is perfectly formatted. PRESERVE ORIGINAL CONTENT: "
            "You MUST preserve all original bullet points, details, and metrics from the "
            "candidate's Projects and Professional Experience sections. DO NOT truncate, "
            "summarize, or minimize the original project descriptions and work experience. Make proper formatting but preserve the full length."
        )
    
    prompt = f"""You are a world-class ATS resume formatter and career writer.

I have an original resume along with:
- The target Job Description (JD)
- Refined gap content (new achievements/skills to weave in)
- Approved terminology improvements (JD-aligned rewrites)
- Custom additions (extra info the candidate wants included)

CRITICAL RULES — READ BEFORE OUTPUTTING ANYTHING:
a) The PROFESSIONAL SUMMARY section is MANDATORY. If the original resume has one, use/refine it. If it does not, you MUST generate one. STRICT WORD LIMIT: The length of the summary MUST be 60-80 words for a fresher/entry-level candidate, and 60-110 words for an experienced candidate. Do not exceed these limits so it fits properly on A4 size. Integrate the original content, JD, and (only if provided) gap content/custom additions. DO NOT invent information.
b) For all other sections (CERTIFICATIONS, ACHIEVEMENTS, ADDITIONAL_SECTIONS, PROJECTS), ONLY include them if they actually exist in the Original Resume OR if they were explicitly provided in the Custom Additions (e.g., prefixed with 'certificate:'). Do NOT create them otherwise.
c) In the EDUCATION section, the "heading" field must be plain text (e.g. "MBA in Human Resources | Gujarat Technological University | 2023 - 2025"). If the original resume includes a percentage or CGPA (e.g. "8.5 CGPA", "85%"), you MUST include it as a bullet inside that education item's "bullets" array.
d) Never output empty arrays as section placeholders — if a section has no real content from the original resume, omit it entirely.

⚡ ATS SCORE IMPROVEMENT RULES (MANDATORY — These directly raise the ATS score):
ATS-1. KEYWORD SATURATION: Extract ALL important keywords, skills, and technologies from the JD. Every keyword that is already present in the resume MUST appear at least once in the Technical Skills section, PLUS be woven naturally into the Professional Summary. Do NOT keyword-stuff bullet points — place keywords in Skills and Summary.
ATS-2. TECHNICAL SKILLS ENRICHMENT: Scan the JD for every technology, tool, library, or methodology mentioned. If the candidate's original resume shows evidence of that skill anywhere (in projects, experience, certifications, or coursework), ADD it to the TECHNICAL SKILLS section even if it was not there before. You are allowed to add skills to the skills section if they are verifiably evidenced elsewhere in the resume.
ATS-3. JD TITLE IN SUMMARY: The PROFESSIONAL SUMMARY MUST contain the exact job title from the JD (e.g., "Data Scientist", "Software Engineer") within the first sentence. ATS parsers check for this.
ATS-4. ACTION VERBS: Start every bullet point with a strong, JD-relevant action verb (Developed, Implemented, Designed, Engineered, Analyzed, Optimized, Built, Deployed, Architected, Leveraged).
ATS-5. SECTION HEADERS: Use EXACT standard ATS section titles: "PROFESSIONAL SUMMARY", "PROFESSIONAL EXPERIENCE" or "TRAINING EXPERIENCE", "TECHNICAL SKILLS", "EDUCATION", "PROJECTS", "CERTIFICATIONS".
ATS-6. SKILLS FORMAT: In the TECHNICAL SKILLS section, format as "Category: Skill1, Skill2, Skill3" on separate lines. Add JD-relevant skills the candidate demonstrably has based on their project/experience evidence.

Instructions:
1. Integrate all refined gap content logically into the candidate's existing PROFESSIONAL EXPERIENCE or PROJECTS sections as new bullet points. The skills must be attached to real work history to pass ATS context checks. If the gap content cannot logically fit into existing roles, only then add it to the PROFESSIONAL SUMMARY.
2. Apply terminology improvements by replacing original phrasing with exact JD keywords specifically in the Technical Skills, Experience, or Projects sections where they belong. Do not just dump them in the summary; optionally keep original tech in brackets (e.g., "Python (Pandas)").
3. For Custom Additions: if the user explicitly prefixes an addition with a section name (e.g., 'certificate:', 'education:', 'project:'), you MUST create that section if it does not exist (e.g., CERTIFICATIONS, EDUCATION, PROJECTS) and place the item there. Do NOT put certificates, education, or projects into the Professional Summary. If a line is prefixed with 'about me:' or 'professional summary:' (case-insensitive), treat that content as the professional summary material and merge it into the PROFESSIONAL SUMMARY section — do NOT place it in any other section. If no prefix is given, incorporate it into the most logical section.
4. STRICT RULE: NEVER fabricate dates, years, companies, percentages, or ANY numerical metrics. You are STRICTLY FORBIDDEN from mentioning any numerical values in the updated resume unless they are explicitly present in the Original Resume or explicitly provided by the user in the Custom Additions/Gaps. Preserve any percentage or CGPA values present in the Education section.
5. Keep bullet points concise, start with strong action verbs, and quantify only when data exists in the original resume or user input. DO NOT use bold or markdown formatting (like **bold**) within the text of any section, especially custom additions. For certificates, simply list the name and agency/score without adding extra verbs like "Completed".
{page_limit_rule}
7. Produce clean, professional output that passes ATS keyword scanning for the provided JD without keyword stuffing or repetitive phrasing.
8. Do NOT add new job experiences, companies, dates, or achievements unless they come from Refined Gap Content or Custom Additions. (Exception 1: You MUST generate a Professional Summary if missing). (Exception 2: Per ATS-2, you MAY enrich the TECHNICAL SKILLS section with JD-relevant skills that are verifiably evidenced in the candidate's existing projects, coursework, or certifications).
9. HYPERLINKS & BACKLINKING: You MUST preserve ALL hyperlinks/URLs from the original resume and Custom Additions. Format them EXACTLY as HTML tags in your JSON output like this: <a href="URL" color="blue">Link Text</a>. You must do this for the contact header (e.g., <a href="URL" color="blue">LinkedIn</a>) and any project links. Do NOT strip URLs.
10. CONTACT HEADER FORMATTING: In the "contact" string of the header, you MUST separate each item (phone, email, links) with a " | " character with spaces around it. E.g., "phone | email | <a href...>LinkedIn</a> | <a href...>GitHub</a>".

Output JSON with sections in this order (PROFESSIONAL SUMMARY is mandatory, ONLY include other sections if they exist in the original resume or are explicitly requested via Custom Additions): PROFESSIONAL SUMMARY, EDUCATION, PROFESSIONAL EXPERIENCE (if any), TECHNICAL SKILLS, PROJECTS (if present), CERTIFICATIONS (if present), ACHIEVEMENTS (if present), then any other original sections. Return ONLY valid JSON (no markdown, no commentary):
{{
  "header": {{
    "name": "Full Name",
    "contact": "email | phone | location | LinkedIn"
  }},
  "sections": [
    {{
      "title": "PROFESSIONAL SUMMARY",
      "type": "paragraph",
      "content": "3-4 sentence ATS-optimised summary."
    }},
    {{
      "title": "EDUCATION",
      "type": "items",
      "items": [
        {{
          "heading": "Degree | University | Year",
          "bullets": ["CGPA: X.X / Percentage: XX% (only if present in original)"]
        }}
      ]
    }},
    {{
      "title": "PROFESSIONAL EXPERIENCE",
      "type": "items",
      "items": [
        {{
          "heading": "Job Title | Company | Start - End",
          "bullets": ["Achievement bullet 1", "Achievement bullet 2", "Achievement bullet 3", "Achievement bullet 4", "Achievement bullet 5"]
        }}
      ]
    }},
    {{
      "title": "TECHNICAL SKILLS",
      "type": "bullets",
      "content": ["Category: Skill1, Skill2"]
    }}
  ]
}}

--- Original Resume ---
{resume_text}

--- Refined Gap Content to Integrate ---
{accepted_texts if accepted_texts.strip() else "None"}

--- Approved Terminology Improvements ---
{improvements_text if improvements_text.strip() else "None"}

--- Custom Additions ---
{custom_text if custom_text.strip() else "None"}

--- Target Job Description ---
{jd_text}
"""
    
    messages = [{"role": "user", "content": prompt}]
    content_str = await _call_llm_async(model_name, messages, temperature=0.2, max_tokens=4000)
    content_str = _strip_markdown_json(content_str)
    resume_data = json.loads(content_str)
    
    # Ensure PROFESSIONAL SUMMARY is always the first section
    sections = resume_data.get("sections", [])
    summary_idx = next(
        (i for i, s in enumerate(sections) if s.get("title", "").upper() == "PROFESSIONAL SUMMARY"),
        None
    )
    if summary_idx is not None and summary_idx != 0:
        sections.insert(0, sections.pop(summary_idx))
        resume_data["sections"] = sections
    
    # Build PDF from JSON
    buffer = BytesIO()
    MARGIN = 18 * mm
    
    is_two_col = "Two Column" in template_name or "Two-Column" in template_name
    if is_two_col:
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            rightMargin=10 * mm, leftMargin=10 * mm,
            topMargin=12 * mm, bottomMargin=12 * mm
        )
    else:
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            rightMargin=MARGIN, leftMargin=MARGIN,
            topMargin=14 * mm, bottomMargin=14 * mm
        )
    
    story = []
    styles = getSampleStyleSheet()
    
    # Text sanitization for PDF
    def sanitize_text(text: str) -> str:
        if not isinstance(text, str):
            return text
        replacements = {
            "\u2013": "-", "\u2014": "-", "\u2011": "-",
            "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
            "\u25a0": "-", "\u00a0": " ", "\u200b": ""
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
            
        import re
        # 1. Convert markdown links to html links: [text](URL) -> <a href="URL">text</a>
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
        
        # 2. Escape lone ampersands (but not if they are part of &amp; or &lt; etc)
        text = re.sub(r'&(?!(amp|lt|gt|quot|apos);)', '&amp;', text)
        
        # 3. Convert all <a> tags to ReportLab <link> with explicit blue color and underline
        # e.g. <a href="URL" color="blue">text</a> -> <font color="#005b96"><u><link href="URL">text</link></u></font>
        text = re.sub(
            r'<a[^>]*href=[\'"]([^\'"]+)[\'"][^>]*>(.*?)</a>', 
            r'<font color="#005b96"><u><link href="\1">\2</link></u></font>', 
            text
        )
        return text
    
    def sanitize_json(data):
        if isinstance(data, dict):
            return {k: sanitize_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [sanitize_json(v) for v in data]
        else:
            return sanitize_text(data)
    
    resume_data = sanitize_json(resume_data)
    
    # Filter empty sections
    filtered_sections = []
    for sec in resume_data.get("sections", []):
        sec_type = sec.get("type", "")
        if sec_type == "bullets" and not sec.get("content"):
            continue
        if sec_type == "items" and not sec.get("items"):
            continue
        filtered_sections.append(sec)
    resume_data["sections"] = filtered_sections
    
    # Colors and typography
    primary_color = colors.HexColor("#1a1a2e")
    accent_color = colors.HexColor("#1a1a2e")
    text_color = colors.HexColor("#333333")
    heading_font = "Helvetica-Bold"
    body_font = "Helvetica"
    
    if "blue" in template_name.lower():
        primary_color = colors.HexColor("#005b96")
        accent_color = colors.HexColor("#03396c")
    elif is_two_col:
        primary_color = colors.HexColor("#000000")
        accent_color = colors.HexColor("#444444")
    
    base_font_size = 11 if is_two_col else 10.5
    base_leading = 14.5 if is_two_col else 14.5
    
    # Define styles
    name_style = ParagraphStyle(
        "Name", parent=styles["Normal"],
        fontName=heading_font, fontSize=22,
        alignment=TA_CENTER,
        spaceBefore=0, spaceAfter=6,
        leading=26,
        textColor=primary_color
    )
    
    contact_style = ParagraphStyle(
        "Contact", parent=styles["Normal"],
        fontName=body_font, fontSize=10.5,
        alignment=TA_CENTER,
        spaceBefore=0, spaceAfter=10,
        leading=14,
        textColor=colors.HexColor("#444444")
    )
    
    section_heading_style = ParagraphStyle(
        "SectionHeading", parent=styles["Normal"],
        fontName=heading_font, fontSize=12,
        spaceBefore=12, spaceAfter=3,
        leading=16, leftIndent=0,
        textColor=primary_color
    )
    
    item_heading_style = ParagraphStyle(
        "ItemHeading", parent=styles["Normal"],
        fontName=heading_font, fontSize=11,
        spaceBefore=8, spaceAfter=2,
        textColor=colors.HexColor("#222222"), leading=14
    )
    
    edu_heading_style = ParagraphStyle(
        "EduHeading", parent=styles["Normal"],
        fontName=body_font, fontSize=base_font_size,
        spaceBefore=6, spaceAfter=1,
        textColor=colors.HexColor("#222222"), leading=base_leading
    )
    
    bullet_style = ParagraphStyle(
        "Bullet", parent=styles["Normal"],
        fontName="Helvetica", fontSize=base_font_size,
        leading=base_leading, spaceAfter=4,
        textColor=colors.HexColor("#333333")
    )
    
    paragraph_style = ParagraphStyle(
        "Para", parent=styles["Normal"],
        fontName="Helvetica", fontSize=base_font_size,
        leading=base_leading, spaceAfter=8,
        textColor=colors.HexColor("#333333")
    )
    
    # Header
    header = resume_data.get("header", {})
    if header.get("name"):
        story.append(Paragraph(header["name"].upper(), name_style))
    if header.get("contact"):
        story.append(Paragraph(header["contact"], contact_style))
    
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1a1a2e"), spaceAfter=6))
    
    # Sections
    left_flowables = []
    right_flowables = []
    left_section_titles = ["PROFESSIONAL SUMMARY", "PROFESSIONAL EXPERIENCE", "PROJECTS", "EXPERIENCE", "SUMMARY"]
    
    for section in resume_data.get("sections", []):
        section_flowables = []
        title = section.get("title", "").upper()
        if title:
            section_flowables.append(Paragraph(title, section_heading_style))
            section_flowables.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc"), spaceAfter=4))
        
        sec_type = section.get("type", "")
        
        if sec_type == "paragraph":
            section_flowables.append(Paragraph(section.get("content", ""), paragraph_style))
        
        elif sec_type == "bullets":
            items = []
            for b in section.get("content", []):
                items.append(ListItem(Paragraph(b, bullet_style), leftIndent=14, bulletOffsetY=-1.5))
            if items:
                section_flowables.append(ListFlowable(items, bulletType="bullet", start="•", leftIndent=12))
        
        elif sec_type == "items":
            is_education = title == "EDUCATION"
            heading_s = edu_heading_style if is_education else item_heading_style
            for item in section.get("items", []):
                if item.get("heading"):
                    section_flowables.append(Paragraph(item["heading"], heading_s))
                bullets = item.get("bullets", [])
                if bullets:
                    b_items = [
                        ListItem(Paragraph(b, bullet_style), leftIndent=14, bulletOffsetY=-1.5)
                        for b in bullets
                    ]
                    section_flowables.append(ListFlowable(b_items, bulletType="bullet", start="•", leftIndent=12))
        
        if not is_two_col:
            section_flowables.append(Spacer(1, 4))
        
        if is_two_col:
            if title in left_section_titles:
                left_flowables.extend(section_flowables)
            else:
                right_flowables.extend(section_flowables)
        else:
            story.extend(section_flowables)
    
    if is_two_col:
        table_data = [[left_flowables, right_flowables]]
        col_widths = [318, 212]
        t = Table(table_data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (0, 0), 20),
        ]))
        story.append(KeepInFrame(0, 0, [t], mode="shrink"))
    
    doc.build(story)
    buffer.seek(0)
    return buffer
