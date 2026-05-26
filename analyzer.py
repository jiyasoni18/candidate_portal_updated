import json
import re
import requests
import fitz  # PyMuPDF
from typing import Dict, Any
from datetime import date
from io import BytesIO

# ─────────────────────────────────────────────────────────────────────────────
#  Model constants (centralised – easy to swap)
# ─────────────────────────────────────────────────────────────────────────────
MODEL_PARSER_PRIMARY  = "openai/gpt-oss-120b"     # GPT-OSS 120B – parsing & cleaning
MODEL_PARSER_FALLBACK = "openai/gpt-oss-20b"      # GPT-OSS 20B  – fallback when 402/429
MODEL_ANALYSIS        = "google/gemini-3-flash-preview"  # Scoring & gap/improvement detection
MODEL_REFINE          = "openai/gpt-oss-120b"     # Batch gap + custom text refinement
MODEL_PDF             = "openai/gpt-oss-120b"     # ATS-friendly resume JSON generation

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# ─────────────────────────────────────────────────────────────────────────────
#  Helper: raw API call (raises on HTTP error)
# ─────────────────────────────────────────────────────────────────────────────
def _call_llm(api_key: str, model: str, messages: list, temperature: float = 0.2, max_tokens: int = 2000) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://jd-resume-analyzer.local",
        "X-Title": "JD Resume Matcher"
    }
    data = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    resp = requests.post(OPENROUTER_URL, headers=headers, json=data, timeout=180)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _strip_markdown_json(text: str) -> str:
    """Remove ```json ... ``` fences if present."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


# ─────────────────────────────────────────────────────────────────────────────
#  Step 0: PDF text extraction
# ─────────────────────────────────────────────────────────────────────────────
def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from a PDF file using PyMuPDF (fitz) and preserve hyperlinks."""
    doc = fitz.open(pdf_path)
    text = ""
    links_info = []
    for page in doc:
        text += page.get_text() + "\n"
        for link in page.get_links():
            if link.get("uri"):
                # Get the text that the hyperlink covers
                link_text = page.get_textbox(link["from"]).strip().replace('\n', ' ')
                if link_text:
                    links_info.append(f"URL provided for '{link_text}': {link['uri']}")
                else:
                    links_info.append(f"URL provided: {link['uri']}")
                    
    if links_info:
        # Remove duplicates
        unique_links = []
        for l in links_info:
            if l not in unique_links:
                unique_links.append(l)
        text += "\n\n--- EXTRACTED HYPERLINKS FROM ORIGINAL RESUME ---\n"
        text += "\n".join(unique_links)
        
    return text


# ─────────────────────────────────────────────────────────────────────────────
#  Step 1: Parse & clean text
# ─────────────────────────────────────────────────────────────────────────────
def parse_document_text(raw_text: str, doc_type: str, api_key: str) -> str:
    """
    Cleans up the extracted raw text natively using Python to eliminate LLM latency.
    """
    import re
    # Remove excessive newlines and spaces
    cleaned = re.sub(r'\n{3,}', '\n\n', raw_text)
    cleaned = re.sub(r' {3,}', '  ', cleaned)
    return cleaned.strip()


# ─────────────────────────────────────────────────────────────────────────────
#  Step 2: Scoring, gap detection, and improvement detection
# ─────────────────────────────────────────────────────────────────────────────
def analyze_resume_jd(resume_text: str, jd_text: str, api_key: str,
                      model_name: str = MODEL_ANALYSIS) -> Dict[str, Any]:
    """
    Analyses a Resume against a Job Description.
    Returns a structured dict with match_score, is_match, gaps, improvements, summary, explanation.
    """
    prompt = f"""
You are an expert technical recruiter and Applicant Tracking System (ATS).
The current date is {date.today().strftime("%B %Y")}. When a candidate lists their experience as 'Present' or 'till now', calculate their experience up to {date.today().strftime("%B %Y")}.
Analyse the provided Resume against the provided Job Description and produce a JSON response with the following keys:
- "match_score": Integer 0‑100 representing overall fit.
- "is_match": Boolean (true if match_score >= 70).
- "ats_score": Integer 0-100 representing how ATS-friendly the original resume is (based on structure, formatting, and keyword optimization).
- "ats_explanation": A short explanation for the given ats_score.
- "gaps": List of strings describing missing skills, experience, or project evidence. CRITICAL: ONLY list gaps for skills or requirements that are EXPLICITLY mentioned in the Job Description but missing from the resume. If the match_score is less than 95, you MUST provide at least one gap or improvement explaining exactly what is missing or could be improved to reach a 95/100 score.
- "improvements": List of strings describing terminology improvements. CRITICAL: ONLY suggest improvements if the Job Description EXPLICITLY asks for a specific keyword AND the resume contains a related concept that can be rewritten to match the JD's terminology. If there are no such terminology mismatches based on the JD, leave this list EMPTY []. Do not suggest random or generic improvements.
- "core_strengths": List of 3-5 strings describing the candidate's core strengths and standout qualifications that directly align with the core requirements of the JD. Highlight their strongest selling points.
- "summary": 2‑3 sentence high‑level summary of the candidate's suitability.

CRITICAL INSTRUCTION: "gaps" and "improvements" must be mutually exclusive. If a skill is flagged as an "improvement" (because the candidate possesses a related skill that maps to the JD), it means the candidate effectively HAS the skill. Therefore, you MUST NOT list that same skill under "gaps".
- "explanation": A concise paragraph explaining how the score was calculated, e.g., weighting of years of experience, technical skills, projects, and JD seniority level (freshers vs experienced).

**Scoring guidelines**:
1. Years of Experience: Carefully sum the duration of ALL professional roles and internships listed in the resume to calculate the candidate's TOTAL years of experience. Then, determine how much of that experience is strictly relevant to the JD's field. If the JD explicitly specifies a required number of years of experience, count any relevant internship experience toward that requirement. Score this component out of a maximum of 15 points. If the JD does NOT specify years of experience, evaluate the candidate's overall experience level and score this component out of a maximum of 10 points. In your "summary" and "explanation", you MUST explicitly state the candidate's total calculated experience (e.g. "Candidate has a total of 3 years of experience, with 2 years specifically in AI...") so the user knows you counted all roles.
CRITICAL RULE FOR FRESHERS: If the JD welcomes freshers (or doesn't require experience) and the candidate is a fresher, give them full credit for internships, coursework, and academic projects. Do NOT deduct marks for lacking "real" industry experience. However, if the JD explicitly requires industry experience and the candidate is a fresher, deduct points accordingly.
2. Core Technical Skills: Contribute up to 45 points (or 50 points if experience was 10). Deduct points for missing critical skills.
3. Projects and Practical Depth: Strong projects and practical applications contribute up to 30 points.
4. Soft-skills and Domain Knowledge: Contribute up to 10 points.
5. The final match_score must be the sum of these weighted components, totalling a maximum of 100.

Only output the valid JSON. Do not include markdown formatting like ```json.

Job Description:
{jd_text}

Resume:
{resume_text}
"""
    messages = [{"role": "user", "content": prompt}]
    result_text = _call_llm(api_key, model_name, messages, temperature=0.1, max_tokens=1500)
    result_text = _strip_markdown_json(result_text)
    return json.loads(result_text)


# ─────────────────────────────────────────────────────────────────────────────
#  Step 3a: Batch gap + custom text refinement
# ─────────────────────────────────────────────────────────────────────────────
def parse_custom_additions(custom_text: str) -> dict:
    """Parse custom additions into categorized sections.
    Recognises lines like "certificate: <text>", "education: <text>".
    Returns a dict with keys 'certificates', 'education', 'additional' containing lists of strings.
    """
    sections = {"certificates": [], "education": [], "additional": []}
    if not custom_text:
        return sections
    # Split by newlines and commas
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

def refine_all_gaps_and_custom_batch(gaps_data: dict, custom_text: str, jd_text: str,
                                     api_key: str, model_name: str = MODEL_REFINE) -> dict:
    """
    Refines ALL gap notes AND the custom additions in ONE single API call using GPT-OSS 120B.

    gaps_data: dict mapping str(index) -> {"gap": str, "note": str}
    custom_text: free-form additional content the user wants added to the resume

    Returns:
      {
        "gaps": {"0": "refined paragraph", "1": "..."},
        "custom": "refined custom additions paragraph"
      }
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
A) For each gap, transform the user notes into a concise, professional, ATS-friendly paragraph addressing that gap (MAXIMUM 2-3 sentences). Make sure the phrasing, keywords, and tone align strongly with the target Job Description. Be specific – use action verbs, but STRICTLY DO NOT invent, hallucinate, or mention any numerical metrics, numbers, or percentages (e.g., 15%, 20%, 3x) unless they are explicitly provided by the user in their notes.
B) If custom additions are provided, rewrite them as polished, ATS-friendly resume content. IF the user prefixed an addition with a specific section (e.g., "certificate: ...", "education: ..."), YOU MUST PRESERVE THAT PREFIX in your rewritten output. For certificates, output the exact name of the certificate, the agency, and the score if provided; DO NOT add extra words like "Completed " before it, and DO NOT use any bold formatting (**). DO NOT merge distinct sections into a single paragraph; keep them separated by newlines if necessary. DO NOT invent or hallucinate metrics or numbers.

Return ONLY a valid JSON object in this exact schema:
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
    content_str = _call_llm(api_key, model_name, messages, temperature=0.2, max_tokens=2000)
    content_str = _strip_markdown_json(content_str)
    return json.loads(content_str)


# ─────────────────────────────────────────────────────────────────────────────
#  Kept for backward-compatibility (single gap refine – not used in batch flow)
# ─────────────────────────────────────────────────────────────────────────────
def refine_gap_notes(gap: str, note: str, api_key: str, model_name: str = MODEL_REFINE) -> str:
    prompt = (f"You are an expert resume writer. Transform the following notes into a concise, "
              f"ATS-friendly paragraph that addresses the gap: '{gap}'. "
              f"Use the user's notes as source material. Output only the refined paragraph.")
    messages = [{"role": "user", "content": prompt + "\n\nUser notes:\n" + note}]
    refined = _call_llm(api_key, model_name, messages, temperature=0.2, max_tokens=500)
    return refined.strip("`").strip()


# ─────────────────────────────────────────────────────────────────────────────
#  Step 4: ATS-friendly resume JSON generation
# ─────────────────────────────────────────────────────────────────────────────
def generate_ats_resume_json(resume_text: str, accepted_texts: str, improvements_text: str,
                              custom_text: str, jd_text: str, api_key: str,
                              template_name: str, model_name: str = MODEL_PDF) -> dict:
    """
    Uses GPT-OSS 120B to integrate all inputs and return a structured JSON resume.
    """
    page_limit_rule = "6. Ensure the final resume is perfectly formatted. PRESERVE ORIGINAL CONTENT: You MUST preserve all original bullet points, details, and metrics from the candidate's Projects and Professional Experience sections. DO NOT truncate, summarize, or minimize the original project details. Only add to them."
    
    if "Two-Column" in template_name:
        page_limit_rule = "6. STRICT PAGE LIMIT (MAXIMUM 1 A4 PAGE): While you must fit the content on one page, DO NOT arbitrarily delete or minimize the candidate's core Projects or Professional Experience. Preserve the depth of their technical projects exactly as they are in the original resume."

    prompt = f"""You are a world-class ATS resume formatter and career writer.

I have an original resume along with:
- The target Job Description (JD)
- Refined gap content (new achievements/skills to weave in)
- Approved terminology improvements (JD-aligned rewrites)
- Custom additions (extra info the candidate wants included)

CRITICAL RULES — READ BEFORE OUTPUTTING ANYTHING:
a) The PROFESSIONAL SUMMARY section is MANDATORY. If the original resume has one, use/refine it. If it does not, you MUST generate a concise 3-4 sentence summary using the original content, JD, and (only if provided by the user) gap content/custom additions. DO NOT invent information.
b) For all other sections (CERTIFICATIONS, ACHIEVEMENTS, ADDITIONAL_SECTIONS, PROJECTS), ONLY include them if they actually exist in the Original Resume OR if they were explicitly provided in the Custom Additions (e.g., prefixed with 'certificate:'). Do NOT create them otherwise.
c) In the EDUCATION section, the "heading" field must be plain text (e.g. "MBA in Human Resources | Gujarat Technological University | 2023 - 2025"). If the original resume includes a percentage or CGPA (e.g. "8.5 CGPA", "85%"), you MUST include it as a bullet inside that education item's "bullets" array.
d) Never output empty arrays as section placeholders — if a section has no real content from the original resume, omit it entirely.

Instructions:
1. Integrate refined gap content into the PROFESSIONAL EXPERIENCE or PROJECTS sections where it logically fits as new bullet points. DO NOT shove all gaps into the Professional Summary. Only put them in the summary if they are high-level overviews.
2. Apply terminology improvements by replacing original phrasing with exact JD keywords specifically in the Technical Skills, Experience, or Projects sections where they belong. Do not just dump them in the summary; optionally keep original tech in brackets (e.g., "Python (Pandas)").
3. For Custom Additions: if the user explicitly prefixes an addition with a section name (e.g., 'certificate:', 'education:'), you MUST create that section if it does not exist (e.g., CERTIFICATIONS, EDUCATION) and place the item there. Do NOT put certificates or education into the Professional Summary or Projects. If no prefix is given, incorporate it into the most logical section.
4. STRICT RULE: NEVER fabricate dates, years, companies, percentages, or ANY numerical metrics. You are STRICTLY FORBIDDEN from mentioning any numerical values in the updated resume unless they are explicitly present in the Original Resume or explicitly provided by the user in the Custom Additions/Gaps. Preserve any percentage or CGPA values present in the Education section.
5. Keep bullet points concise, start with strong action verbs, and quantify only when data exists in the original resume or user input. DO NOT use bold or markdown formatting (like **bold**) within the text of any section, especially custom additions. For certificates, simply list the name and agency/score without adding extra verbs like "Completed".
{page_limit_rule}
7. Produce clean, professional output that passes ATS keyword scanning for the provided JD without keyword stuffing or repetitive phrasing.
8. Do NOT add new sections, skills, experiences, or bullets unless they come from Refined Gap Content or Custom Additions. (Exception: You MUST generate a Professional Summary if missing). Preserve all original sections exactly as they appear.
9. HYPERLINKS & BACKLINKING: If the original resume or Custom Additions contain any hyperlinks/URLs (e.g., at the bottom of the extracted text or as plain text URLs), you MUST format them as clickable HTML tags in your JSON output. Format them EXACTLY like this: `<a href="URL" color="blue">Link Text</a>`. Apply this to project links, contact info, and anywhere else a URL is provided. Do not output plain text URLs if you can link them.

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
    content_str = _call_llm(api_key, model_name, messages, temperature=0.2, max_tokens=4000)
    content_str = _strip_markdown_json(content_str)
    resume_data = json.loads(content_str)

    # Ensure PROFESSIONAL SUMMARY is always the first section (in case LLM put it elsewhere)
    sections = resume_data.get('sections', [])
    summary_idx = next((i for i, s in enumerate(sections) if s.get('title', '').upper() == 'PROFESSIONAL SUMMARY'), None)
    if summary_idx is not None and summary_idx != 0:
        sections.insert(0, sections.pop(summary_idx))
        resume_data['sections'] = sections

    return resume_data


# ─────────────────────────────────────────────────────────────────────────────
#  Step 5: Build PDF from JSON
# ─────────────────────────────────────────────────────────────────────────────
def build_pdf_from_json(resume_data: dict, template_name: str = "Classic ATS") -> BytesIO:
    """
    Converts the structured JSON output into a clean, ATS-friendly PDF.
    Supports templates: "Classic ATS", "Modern Accent", "Two-Column Professional".
    """
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm, inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, HRFlowable, Table, TableStyle, KeepInFrame
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    buffer = BytesIO()
    MARGIN = 18 * mm

    if "Two-Column" in template_name:
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

    # ── Text Sanitization for PDF ────────────────────────────────────────────
    def sanitize_text(text: str) -> str:
        if not isinstance(text, str):
            return text
        replacements = {
            '\u2013': '-', '\u2014': '-', '\u2011': '-',
            '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"',
            '\u25a0': '-', '■': '-', '\u00a0': ' ', '\u200b': ''
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
        return text

    def sanitize_json(data):
        if isinstance(data, dict):
            return {k: sanitize_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [sanitize_json(v) for v in data]
        else:
            return sanitize_text(data)

    resume_data = sanitize_json(resume_data)

    filtered_sections = []
    for sec in resume_data.get('sections', []):
        sec_type = sec.get('type', '')
        if sec_type == 'bullets' and not sec.get('content'):
            continue
        if sec_type == 'items' and not (sec.get('items') or []):
            continue
        filtered_sections.append(sec)
    resume_data['sections'] = filtered_sections

    # ── Colors & Typography per Template ─────────────────────────────────────
    primary_color = colors.HexColor('#1a1a2e')
    accent_color = colors.HexColor('#1a1a2e')
    text_color = colors.HexColor('#333333')
    heading_font = 'Helvetica-Bold'
    body_font = 'Helvetica'
    
    if "Blue" in template_name:
        primary_color = colors.HexColor('#005b96')
        accent_color = colors.HexColor('#03396c')
    else:
        primary_color = colors.HexColor('#000000') if "Two-Column" in template_name else colors.HexColor('#1a1a2e')
        accent_color = colors.HexColor('#444444') if "Two-Column" in template_name else colors.HexColor('#1a1a2e')

    name_style = ParagraphStyle(
        'Name', parent=styles['Normal'],
        fontName=heading_font, fontSize=22,
        alignment=TA_LEFT if "Two-Column" in template_name else TA_CENTER,
        spaceBefore=0, spaceAfter=6,
        leading=26,
        textColor=primary_color
    )
    contact_style = ParagraphStyle(
        'Contact', parent=styles['Normal'],
        fontName=body_font, fontSize=10 if "Two-Column" in template_name else 10.5,
        alignment=TA_LEFT if "Two-Column" in template_name else TA_CENTER,
        spaceBefore=0, spaceAfter=10,
        leading=14,
        textColor=colors.HexColor('#444444')
    )
    # Use tighter spacing for Two-Column to prevent extreme shrinking, but keep font readable
    is_two_col = ("Two-Column" in template_name)
    base_font_size = 11 if is_two_col else 10.5
    base_leading = 14.5 if is_two_col else 14.5

    section_heading_style = ParagraphStyle(
        'SectionHeading', parent=styles['Normal'],
        fontName=heading_font, fontSize=12 if is_two_col else 12,
        spaceBefore=10 if is_two_col else 12, spaceAfter=3 if is_two_col else 4,
        leading=15 if is_two_col else 16, leftIndent=0,
        textColor=primary_color
    )
    item_heading_style = ParagraphStyle(
        'ItemHeading', parent=styles['Normal'],
        fontName=heading_font, fontSize=11.5 if is_two_col else 11,
        spaceBefore=6 if is_two_col else 8, spaceAfter=2 if is_two_col else 3,
        textColor=colors.HexColor('#222222'), leading=14 if is_two_col else 14
    )
    edu_heading_style = ParagraphStyle(
        'EduHeading', parent=styles['Normal'],
        fontName=body_font, fontSize=base_font_size,
        spaceBefore=3 if is_two_col else 6, spaceAfter=1 if is_two_col else 2,
        textColor=colors.HexColor('#222222'), leading=base_leading
    )
    bullet_style = ParagraphStyle(
        'Bullet', parent=styles['Normal'],
        fontName='Helvetica', fontSize=base_font_size,
        leading=base_leading, spaceAfter=2 if is_two_col else 4,
        textColor=colors.HexColor('#333333')
    )
    paragraph_style = ParagraphStyle(
        'Para', parent=styles['Normal'],
        fontName='Helvetica', fontSize=base_font_size,
        leading=base_leading, spaceAfter=4 if is_two_col else 8,
        textColor=colors.HexColor('#333333')
    )

    # ── Header ───────────────────────────────────────────────────────────────
    header = resume_data.get("header", {})
    if header.get("name"):
        story.append(Paragraph(header["name"].upper(), name_style))
    if header.get("contact"):
        story.append(Paragraph(header["contact"], contact_style))

    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1a1a2e'), spaceAfter=6))

    # ── Sections ─────────────────────────────────────────────────────────────
    left_flowables = []
    right_flowables = []
    
    left_section_titles = ["PROFESSIONAL SUMMARY", "PROFESSIONAL EXPERIENCE", "PROJECTS", "EXPERIENCE", "SUMMARY"]

    for section in resume_data.get("sections", []):
        section_flowables = []
        title = section.get("title", "").upper()
        if title:
            section_flowables.append(Paragraph(title, section_heading_style))
            section_flowables.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#cccccc'), spaceAfter=4))

        sec_type = section.get("type", "")

        if sec_type == "paragraph":
            section_flowables.append(Paragraph(section.get("content", ""), paragraph_style))

        elif sec_type == "bullets":
            items = []
            for b in section.get("content", []):
                items.append(
                    ListItem(Paragraph(b, bullet_style), leftIndent=14, bulletOffsetY=-1.5)
                )
            if items:
                section_flowables.append(ListFlowable(items, bulletType='bullet', start='•', leftIndent=12))

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
                    section_flowables.append(ListFlowable(b_items, bulletType='bullet', start='•', leftIndent=12))

        if not is_two_col:
            section_flowables.append(Spacer(1, 4))
        
        # Route flowables based on template
        if is_two_col:
            if title in left_section_titles:
                left_flowables.extend(section_flowables)
            else:
                right_flowables.extend(section_flowables)
        else:
            story.extend(section_flowables)

    if is_two_col:
        # Create a table to hold the two columns side by side
        # A4 width is 210mm (~595 points). Left margin 10mm, Right margin 10mm.
        # Usable width = 190mm (~538 points).
        # We assign roughly 63% to the left column and 35% to the right column, leaving a small gap.
        table_data = [[left_flowables, right_flowables]]
        col_widths = [318, 212]
        t = Table(table_data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (0,0), 20), # Wider gap between columns
        ]))
        story.append(KeepInFrame(0, 0, [t], mode='shrink'))

    doc.build(story)
    buffer.seek(0)
    return buffer
