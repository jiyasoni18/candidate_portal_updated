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
import logging

logger = logging.getLogger(__name__)

# Model constants — purpose-specific model assignments
# Gap analysis & ATS scoring (fast, smart analysis)
MODEL_ANALYSIS = "google/gemini-3-flash-preview"
# Gap/input refinement and custom additions (large context, high quality rewriting)
MODEL_REFINE = "openai/gpt-oss-120b"
# PDF resume generation (large context, precise instruction-following)
MODEL_PDF = "openai/gpt-oss-120b"


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
    limit_tokens = min(max_tokens, 1200)
    response = await call_openrouter(system_prompt, user_content, model, max_tokens=limit_tokens)
    return response


def _strip_markdown_json(text: str) -> str:
    """Extract JSON from Markdown fences, ignoring conversational text."""
    # First, try to find a markdown code block
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1).strip()
    
    # Second, to handle extra conversational text before or after the JSON,
    # find the outermost '{...}' or '[...]'
    start_dict = text.find('{')
    end_dict = text.rfind('}')
    
    start_list = text.find('[')
    end_list = text.rfind(']')
    
    # Determine which one encapsulates the most content
    dict_len = end_dict - start_dict if start_dict != -1 and end_dict != -1 else -1
    list_len = end_list - start_list if start_list != -1 and end_list != -1 else -1
    
    if dict_len > 0 and dict_len >= list_len:
        return text[start_dict:end_dict+1]
    elif list_len > 0:
        return text[start_list:end_list+1]
        
    return text.strip()


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
  FORMAT: "REPLACE '[resume wording]' WITH '[exact JD term] ([resume wording])'"
  DO NOT put missing skills here. If no wording mismatches exist, return []. List ALL terminology mismatches; do not limit the number.
- "existing_entities": List of strings — EXTRACT all Project names and Company names from the original resume. These will be used for a dropdown. Format: ["Project: [Name]", "Company: [Name]"].
- "targeted_questions": List of strings (max 3-4) — Ask the candidate for MISSING METRICS (e.g. accuracy, scale, performance) or MISSING CONTEXT regarding tools/skills the JD requires that they might have used in their listed experiences but failed to mention. Example: "The JD requires AWS. Did you use AWS in your role at TechCorp?", "You mentioned creating a model, what was the accuracy or scale?"
- "core_strengths": List of 3-5 strings — candidate's strongest JD-aligned qualifications. Use the exact JD terminology where possible.
- "summary": 2-3 sentence overview of suitability for this specific role.

STRICT RULES:
- All output MUST use the exact terminology from the JD, not generic descriptions.
- "improvements" = ONLY cases where skill EXISTS in resume but uses WRONG words vs JD. Never use this for missing skills.
- DO NOT INCLUDE EXACT MATCHES in improvements. If the resume already uses the exact JD term (e.g. "Linear Regression" -> "Linear Regression"), it is NOT an improvement. DO NOT INCLUDE IT.
- DO NOT INCLUDE CASE-ONLY DIFFERENCES. If the only difference between the resume term and the JD term is capitalization (e.g. "Scikit-learn" vs "scikit-learn"), it is NOT an improvement. DO NOT INCLUDE IT.
- DO NOT INCLUDE SELF-REFERENTIAL REPLACEMENTS. If the replacement would result in the same word appearing twice (e.g. "scikit-learn (Scikit-learn)") where both words mean the same thing, do NOT include it.
- DO NOT MAP UNRELATED CONCEPTS in improvements (e.g. do not map "workflow automation" to "Learning & Development", or "agentic concepts" to "Exploratory Data Analysis"). Only map actual synonymous terms that are truly different words (e.g. "Deep Learning" vs "Neural Networks").
- A valid improvement example: REPLACE 'Scikit' WITH 'scikit-learn' (only if resume says "Scikit" and JD says "scikit-learn").
- An INVALID improvement: REPLACE 'Scikit-learn' WITH 'scikit-learn (Scikit-learn)' — this is just a capitalization variant of the same term. FORBIDDEN.
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
    return json.loads(result_text, strict=False)


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
    return json.loads(result_text, strict=False)

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
    # Cache disabled — always run a fresh analysis so changes are reflected immediately


    import asyncio

    ats_result, match_result = await asyncio.gather(
        analyze_ats_score(resume_text, jd_text, model_name),
        analyze_jd_match(resume_text, jd_text, model_name),
        return_exceptions=True,
    )

    if isinstance(ats_result, Exception) and isinstance(match_result, Exception):
        raise ats_result

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
    optimize_projects: bool = False,
    optimize_experience: bool = False,
    optimize_summary: bool = False,
    resume_text: str = "",
    targeted_answers: Optional[Dict[str, str]] = None,
    api_key: Optional[str] = None,
    model_name: str = MODEL_REFINE
) -> Dict[str, Any]:
    """
    Refine gap content, custom additions, and optimize specific sections in a single API call.
    """
    # Only process gaps that have actual user notes/answers
    active_gaps = {idx: data for idx, data in gaps_data.items() if data.get("note", "").strip()}
    
    if not active_gaps and not custom_text.strip() and not (optimize_projects or optimize_experience or optimize_summary):
        return {"gaps": {}, "custom": ""}
    
    gaps_text = "\n".join(
        [f"ID {idx} | Gap: '{data['gap']}' | User Notes: '{data['note']}'"
         for idx, data in active_gaps.items()]
    ) if active_gaps else "None"

    optimization_instructions = ""
    if optimize_projects or optimize_experience or optimize_summary:
        optimization_instructions = "\n\n════════════════════════════════════════════════════════\n"
        optimization_instructions += "SECTION OPTIMIZATION INSTRUCTIONS\n"
        optimization_instructions += "════════════════════════════════════════════════════════\n"
        optimization_instructions += f"You have been asked to rewrite specific sections of the user's original resume to better align with the JD keywords. The original resume is provided below.\n\n"
        
        if optimize_projects:
            optimization_instructions += "PROJECTS OPTIMIZATION:\n"
            optimization_instructions += "- Rewrite the existing PROJECTS section to naturally incorporate JD keywords.\n"
            optimization_instructions += "- For each project rewritten, output a line in the `custom` field starting with: `rewrite_project: [Exact Original Project Name] — [Bullet 1] --- [Bullet 2] --- Tech Stack: [skills]`.\n"
            
        if optimize_experience:
            optimization_instructions += "EXPERIENCE OPTIMIZATION:\n"
            optimization_instructions += "- Rewrite the existing PROFESSIONAL EXPERIENCE section to naturally incorporate JD keywords.\n"
            optimization_instructions += "- For each job rewritten, output a line in the `custom` field starting with: `rewrite_experience: [Exact Original Company Name] | [Job Title] | [Start - End] | [Bullet 1] --- [Bullet 2]`.\n"
            
        if optimize_summary:
            optimization_instructions += "SUMMARY OPTIMIZATION:\n"
            optimization_instructions += "- Rewrite the PROFESSIONAL SUMMARY to naturally incorporate JD keywords.\n"
            optimization_instructions += "- Output a line in the `custom` field starting with: `rewrite_summary: [The rewritten paragraph]`.\n"

        optimization_instructions += "\nCRITICAL: Do NOT fabricate any new metrics, dates, or experiences. Only reword existing content to match JD terminology.\n"
        optimization_instructions += f"\n--- Original Resume ---\n{resume_text}\n"
    
    targeted_answers_text = ""
    if targeted_answers and any(ans.strip() for ans in targeted_answers.values()):
        targeted_answers_text = "\n\n4. Answers to Targeted Questions about missing metrics/context:\n"
        for q, a in targeted_answers.items():
            if a.strip():
                targeted_answers_text += f"Q: {q}\nA: {a}\n\n"
        targeted_answers_text += "For these targeted answers, integrate the user's provided context into the most relevant rewritten Experience or Project bullet. If no logical place exists, output it as an `add_to_project` or `experience_bullet`.\n"

    prompt = f"""You are an expert resume writer and career coach.

You will receive these inputs:
1. The target Job Description (JD).
2. A list of resume gaps with user-provided structured answers for each.
3. Optional custom additions the user wants to include in their resume.
{targeted_answers_text}
{optimization_instructions}

CRITICAL SECTION PLACEMENT RULES (follow these EXACTLY to ensure ATS scoring recognizes the content):

A) For each gap in Gap Notes, read the user's answer carefully:

   TYPE 1 — "GENERATE_PROJECT: [skill] | Name: [name] | Description: [desc]": 
   Generate a realistic project entry. Format as a 2-3 bullet project.
   Prefix output with exactly "project: " so the PDF generator places it in the Projects section.
   Label as "[name]" (or generate a professional, appropriate project name based on the skill if name is missing). Do NOT use a fixed label like 'Self-Learning Project'.
   Use the provided description and any "| User Knowledge: [knowledge]" as the basis for the bullets.
   Make sure to highlight the specific user knowledge provided within the project bullets.
   STRICTLY DO NOT fabricate GitHub links, metrics, or stars. Keep it simple and credible.
   The project generated MUST be normal, easy, and basic (e.g., a simple student, academic, or basic personal/knowledge project showcasing fundamental understanding, NOT a complex enterprise-level, production-grade, or large-scale cloud microservice system).

   TYPE 2 — "ADD_TO_PROJECT: [name]":
   The user wants to add this skill to an existing project. The input may include "(Tech: ...)", "— [Description]", and "| User Knowledge: [note]".
   Generate a polished ATS bullet that combines the description and user knowledge.
   Output format: "add_to_project: [name] | [polished ATS bullet]"

   TYPE 3 — Plain skill note (user described experience or knowledge in free text):
   Check if the note contains " | ATTACH_TO: [name]" — if so, extract the name and route the content there.
   - If ATTACH_TO refers to a project name → output: "add_to_project: [Project Name] | [polished ATS bullet]"
   - If ATTACH_TO refers to a company name → output: "experience_bullet: [Company] | [inferred role if possible] | | [polished ATS bullet]"
   - If no ATTACH_TO, check if user mentioned a specific company name → "experience_bullet: [Company] | | | [bullet]"
   - If no company or project mentioned, but user clearly has knowledge → "skill_note: [polished 2-sentence knowledge statement using JD keywords]"
   Use action verbs and exact JD keywords in all outputs.
   STRICTLY DO NOT add random skills, tools, or experiences that the user did not mention.

B) For Custom Additions, rewrite them as polished, ATS-friendly resume content line by line:

   TYPE 1 — Company/Role/Date/Details format (lines starting with "Company:"):
   Format the output as: "experience_bullet: [Company Name] | [Job Title] | [Start] to [End] | [polished ATS bullet using exact JD keywords]"
   Produce EXACTLY ONE "experience_bullet:" line per company entry. If the user provides multiple achievements in the Details, combine them into the final section separated by " --- " (e.g. bullet 1 --- bullet 2).

   TYPE 2 — "project: [Name] (Tech: ...) — [Description]":
   Format as a new polished project entry with ATS-aligned bullets using JD keywords. Prefix output with exactly "project: ". Combine multiple bullets with " --- " (e.g. project: Project Name — bullet 1 --- bullet 2).

   TYPE 3 — "add_to_project: [Name] (Tech: ...) — [Description]":
   Output format: "add_to_project: [Exact Project Name] | [polished ATS bullet using JD keywords]"

   TYPE 4 — "GENERATE_PROJECT: [Skills] | Name: [Project Name] | Description: [desc]"
   Generate ONE complete, coherent project that tells a SINGLE unified story. Think of it as building one real product or tool that naturally requires ALL the listed skills.

   RULES:
   - Come up with a specific, professional project name (e.g. "Personal Expense Tracker", "Simple Library Management System", "Student Attendance Portal") — NOT a generic name like "Comprehensive Skills Project" and NOT a complex enterprise system. If the Name field is empty, you MUST invent a concise, professional title (max 8 words) that reflects a simple, normal, and basic application built for personal/academic use.
   - Write EXACTLY 3 achievement bullets that tell a connected story:
     • Bullet 1: What was BUILT and WHY (the simple problem it solved). Start with "Built" or "Developed".
     • Bullet 2: The core TECHNICAL IMPLEMENTATION — how the technologies were actually used together. Keep details simple, basic, and credible for an entry-level or personal project.
     • Bullet 3: The OUTCOME or key challenge overcome.
   - Add ONE final bullet starting with "Tech Stack: " listing ALL the technologies.
   - All bullets must flow together as ONE project — NOT separate mini-projects per skill.
   - Do NOT write vague bullets like "Focused on X" or "Explored Y". Write specific, concrete accomplishments.
   - The project generated MUST be normal, easy, and basic (e.g. a simple student, academic, or basic personal/knowledge project showcasing fundamental understanding, NOT a complex enterprise-level, production-grade, or large-scale cloud microservice system).
   - Combine all bullets with " --- " separator.
   - Output format: "project: [Project Name] — [Bullet 1] --- [Bullet 2] --- [Bullet 3] --- Tech Stack: [all skills]"

   EXAMPLE OUTPUT for skills "SQL, Tableau, dbt":
   project: Sales Intelligence Dashboard — Built an end-to-end analytics pipeline to surface weekly revenue trends and churn signals for the sales team --- Engineered dbt transformation models on top of a PostgreSQL warehouse, writing optimized SQL queries to clean, join, and aggregate multi-source data --- Delivered an interactive Tableau dashboard reducing manual reporting time; surfaced 3 KPI anomalies in the first week --- Tech Stack: SQL, dbt, PostgreSQL, Tableau

    Preserve any section prefixes (certificate:, education:, about me:).
   STRICTLY DO NOT add new prefixes or merge distinct sections. Do NOT remove any details provided by the user.

C) TONE & LANGUAGE: Refine descriptions properly and professionally. DO NOT use heavy, overly complex jargon or "fluff" words. Use simple, impactful language that aligns exactly with the terminology from the JD.

D) HYPERLINKS: If user notes contain URLs, preserve them exactly.

E) STRICT RULE: NEVER fabricate dates, company names, numbers, percentages, or GitHub links.

OUTPUT FORMAT (JSON only, no markdown fences, no commentary):
{{
  "gaps": {{
    "0": "project: Data Analytics Dashboard — Built an interactive dashboard using SQL and Tableau to visualize sales trends, highlighting data manipulation skills.",
    "1": "add_to_project: E-Commerce Platform | Integrated PostgreSQL database with normalized schemas and indexed queries to optimize product catalog retrieval performance.",
    "2": "skill_note: Demonstrated proficiency in SQL by designing normalized schemas and writing complex JOIN queries for academic database projects."
  }},
  "custom": "experience_bullet: TechCorp | Data Analyst | Jan 2023 to Jun 2024 | Implemented Linear Regression models using Scikit-learn to predict customer churn, aligned with data science best practices.\\nproject: Customer Churn Predictor (Tech: Python, Pandas) — Developed a machine learning pipeline..."
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
    try:
        return json.loads(content_str, strict=False)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM refine response: {e}\nResponse: {content_str}")
        try:
            with open("debug_llm_failure.txt", "w", encoding="utf-8") as f:
                f.write("--- PROMPT ---\n")
                f.write(prompt)
                f.write("\n\n--- LLM RESPONSE ---\n")
                f.write(content_str)
        except Exception as io_err:
            logger.error(f"Failed to write debug file: {io_err}")
        raise e
    except Exception as e:
        logger.error(f"Failed to parse LLM refine response: {e}\nResponse: {content_str}")
        raise ValueError(f"AI generated invalid response format. Response was: {content_str}") from e


async def reanalyze_gaps(
    resume_text: str,
    jd_text: str,
    custom_additions: str,
    original_gaps_text: str = "",
    model_name: str = MODEL_ANALYSIS
) -> list[str]:
    """
    Fast re-analysis of gaps taking into account the user's newly added experiences and projects.
    Returns a list of skill gaps that are STILL missing.
    """
    prompt = f"""You are an expert technical recruiter. A candidate has some known skill gaps in their resume.
They have written some NEW additions (projects or experiences) to try to fill these gaps.

Your task is to check if the NEW additions successfully demonstrate the skills missing in the known gaps.

--- New Additions ---
{custom_additions}

--- Known Skill Gaps ---
{original_gaps_text}
--------------------------------------------------
Analyze the New Additions. Which of the Known Skill Gaps are STILL MISSING (i.e., the candidate failed to mention or demonstrate them in the New Additions)?
List ONLY the INDICES (numbers) of the gaps that are STILL missing.
If the New Additions are unrelated, gibberish, or do not clearly demonstrate the skill, you MUST return ALL the indices!
For example, if "Gap 0" and "Gap 2" are not covered by the new additions, return [0, 2].
Format as a valid JSON list of integers. Do not include markdown fences or any other text.
Example: [0, 2]
"""
    try:
        messages = [{"role": "user", "content": prompt}]
        result_text = await _call_llm_async(model_name, messages, temperature=0.0, max_tokens=1000)
        result_text = _strip_markdown_json(result_text)
        import json
        gaps_indices = json.loads(result_text, strict=False)
        
        # Map indices back to the exact strings
        original_lines = []
        import re
        for line in original_gaps_text.split("\n"):
            match = re.match(r"^Gap \d+: (.+)$", line.strip())
            if match:
                original_lines.append(match.group(1))

        if isinstance(gaps_indices, list):
            remaining = []
            for i in gaps_indices:
                try:
                    idx = int(i)
                    if 0 <= idx < len(original_lines):
                        remaining.append(original_lines[idx])
                except (ValueError, TypeError):
                    continue
            return remaining
        return original_lines
    except Exception as e:
        # Fallback to returning all original gaps if anything fails
        logger.error(f"reanalyze_gaps LLM call failed: {e}")
        original_lines = []
        import re
        for line in original_gaps_text.split("\n"):
            match = re.match(r"^Gap \d+: (.+)$", line.strip())
            if match:
                original_lines.append(match.group(1))
        return original_lines

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
            "candidate's Projects and Professional Experience sections EXACTLY as they are. DO NOT truncate, "
            "summarize, or minimize the original project descriptions and work experience. DO NOT remove any content from the original resume. Just format it properly and apply the terminology improvements according to the JD."
        )
    
    prompt = f"""You are a world-class ATS resume formatter and career writer.

I have an original resume along with:
- The target Job Description (JD)
- Refined gap content (new achievements/skills to weave in)
- Approved terminology improvements (JD-aligned rewrites)
- Custom additions (extra info the candidate wants included)

CRITICAL RULES — READ BEFORE OUTPUTTING ANYTHING:
a) The PROFESSIONAL SUMMARY section is MANDATORY. If the original resume has one, use/refine it. If it does not, you MUST generate one. STRICT WORD LIMIT: The length of the summary MUST be 60-80 words for a fresher/entry-level candidate, and 60-110 words for an experienced candidate. Do not exceed these limits so it fits properly on A4 size. Integrate the original content, JD, and (only if provided) gap content/custom additions. DO NOT invent information.
b) PRESERVE EXISTING SECTIONS & CONTENT: You MUST preserve and include all sections (such as CERTIFICATIONS, PROJECTS, ACHIEVEMENTS, EDUCATION, PROFESSIONAL EXPERIENCE, etc.) if they exist in the Original Resume. You are STRICTLY FORBIDDEN from dropping or omitting any section, certification, or project item that is present in the original resume. They must all be present in the updated resume.
c) In the EDUCATION section, the "heading" field must be plain text (e.g. "MBA in Human Resources | Gujarat Technological University | 2023 - 2025"). If the original resume includes a percentage or CGPA (e.g. "8.5 CGPA", "85%"), you MUST include it as a bullet inside that education item's "bullets" array.
d) Never output empty arrays as section placeholders — if a section has no real content from the original resume and is not requested via Custom Additions, omit it entirely.

⚡ ATS SCORE IMPROVEMENT RULES (MANDATORY — These directly raise the ATS score):
ATS-1. KEYWORD SATURATION: Extract ALL important keywords, skills, and technologies from the JD. Every keyword that is already present in the resume MUST appear at least once in the Technical Skills section, PLUS be woven naturally into the Professional Summary. Do NOT keyword-stuff bullet points — place keywords in Skills and Summary.
ATS-2. TECHNICAL SKILLS ENRICHMENT: Scan the JD for every technology, tool, library, or methodology mentioned. If the candidate's original resume shows evidence of that skill anywhere (in projects, experience, certifications, or coursework), ADD it to the TECHNICAL SKILLS section even if it was not there before. You are allowed to add skills to the skills section if they are verifiably evidenced elsewhere in the resume.
ATS-3. JD TITLE IN SUMMARY: The PROFESSIONAL SUMMARY MUST contain the exact job title from the JD (e.g., "Data Scientist", "Software Engineer") within the first sentence. ATS parsers check for this.
ATS-4. ACTION VERBS: Start every bullet point with a strong, JD-relevant action verb (Developed, Implemented, Designed, Engineered, Analyzed, Optimized, Built, Deployed, Architected, Leveraged).
ATS-5. SECTION HEADERS: Use EXACT standard ATS section titles: "PROFESSIONAL SUMMARY", "PROFESSIONAL EXPERIENCE" or "TRAINING EXPERIENCE", "TECHNICAL SKILLS", "EDUCATION", "PROJECTS", "CERTIFICATIONS".
ATS-6. SKILLS FORMAT: In the TECHNICAL SKILLS section, format as "Category: Skill1, Skill2, Skill3" on separate lines. Add JD-relevant skills the candidate demonstrably has based on their project/experience evidence.

Instructions:
1. GAP CONTENT PLACEMENT (CRITICAL — this directly determines your ATS score improvement):
   The Refined Gap Content uses prefixes to tell you exactly where to place each item:
   
   a) "experience_bullet: [Company] | [Role] | [Start] to [End] | [bullet text]"
      → Find the matching company in PROFESSIONAL EXPERIENCE. Add the bullet text to that company's bullets list.
      → If the bullet text contains ' --- ', split it and add each part as a separate bullet under that company.
      → If the company is NOT already in the resume, create a new experience entry with the provided company, role, and date, and add the bullet(s).
      → NEVER put experience bullets in the Professional Summary.
   
   b) "project: [Project Name] — [description]"
      → Add as a NEW entry in the PROJECTS section. Create the PROJECTS section if it doesn't exist.
      → If the description contains ' --- ', split it and add each part as a separate bullet.
      → If a URL is present in the text (e.g., "| <a href=...>"), include it as a link in the project heading.
      → NEVER put project content in the Professional Summary.
   
   c) "add_to_project: [Exact Project Name] | [bullet text]"
      → Find the matching project in the PROJECTS section by name. ADD the bullet text to that project's existing bullets.
      → If the bullet text contains ' --- ', split it and add each part as a separate bullet.
      → CRITICAL: Insert the new bullet(s) BEFORE any existing bullet that starts with "Tech Stack:" or "Technologies:". New achievement bullets must always come before the tech stack line.
      → Do NOT create a new project entry. Only append to the named existing project.
      → If no match is found by name, add as a new project entry.

   d) "skill_note: [text]"
      → Incorporate into the PROFESSIONAL SUMMARY as supporting evidence.

   e) "rewrite_project: [Exact Project Name] — [description]"
      → REPLACES the existing project entry with this exact name. Split description by ' --- ' into bullets.

   f) "rewrite_experience: [Exact Company Name] | [Job Title] | [Start - End] | [description]"
      → REPLACES the existing experience entry for this company. Split description by ' --- ' into bullets.

   g) "rewrite_summary: [text]"
      → REPLACES the entire PROFESSIONAL SUMMARY with this text.

   h) Any gap content without a recognized prefix → Use your judgment: if it describes work experience, add as an experience bullet; if it describes a project, add as a project; otherwise, incorporate into the Summary.

2. ORDERING RULES (STRICTLY ENFORCE):
   - EDUCATION: List entries in REVERSE CHRONOLOGICAL order (most recent degree/graduation year FIRST).
   - PROFESSIONAL EXPERIENCE / TRAINING EXPERIENCE: List jobs in REVERSE CHRONOLOGICAL order (most recent/current role FIRST, oldest role LAST).
   - PROJECTS: Maintain the order from the original resume unless a new project is added — new projects go at the END.
   - NEVER reorder a section in a way that puts older dates above newer dates.

2. Apply terminology improvements exactly as instructed in the improvements list. If an improvement says "REPLACE 'X' WITH 'Y (X)'", you MUST replace occurrences of 'X' with 'Y (X)' in the Technical Skills, Experience, or Projects sections. Do NOT alter or remove any other part of the sentence or bullet point. Just swap the exact word.
3. For Custom Additions: if the user explicitly prefixes an addition with a section name (e.g., 'certificate:', 'education:', 'project:', 'achievement:'), you MUST create that section if it does not exist (e.g., CERTIFICATIONS, EDUCATION, PROJECTS, ACHIEVEMENTS) and place the item there. Do NOT put certificates, education, projects, or achievements into the Professional Summary. If a line is prefixed with 'about me:' or 'professional summary:' (case-insensitive), treat that content as the professional summary material and merge it into the PROFESSIONAL SUMMARY section — do NOT place it in any other section. If no prefix is given, incorporate it into the most logical section.
4. STRICT RULE: NEVER fabricate dates, years, companies, percentages, or ANY numerical metrics. You are STRICTLY FORBIDDEN from mentioning any numerical values in the updated resume unless they are explicitly present in the Original Resume or explicitly provided by the user in the Custom Additions/Gaps. Preserve any percentage or CGPA values present in the Education section. You MUST escape any double quotes inside JSON string values with a backslash (e.g., \"word\").
5. Keep bullet points concise, start with strong action verbs, and quantify only when data exists in the original resume or user input. DO NOT use bold or markdown formatting (like **bold**) within the text of any section, especially custom additions. For certificates, simply list the name and agency/score without adding extra verbs like "Completed".
{page_limit_rule}
7. Produce clean, professional output that passes ATS keyword scanning for the provided JD without keyword stuffing or repetitive phrasing.
8. Do NOT add new job experiences, companies, dates, or achievements unless they come from Refined Gap Content or Custom Additions. (Exception 1: You MUST generate a Professional Summary if missing). (Exception 2: Per ATS-2, you MAY enrich the TECHNICAL SKILLS section with JD-relevant skills that are verifiably evidenced in the candidate's existing projects, coursework, or certifications). (Exception 3: You MUST extract the core skill keywords from any unaddressed skill gaps in the original text and seamlessly add them to the TECHNICAL SKILLS section as a comma-separated list. This is mandatory for ATS optimization).
9. HYPERLINKS & BACKLINKING (CRITICAL): You MUST preserve ALL hyperlinks/URLs from the original resume and Custom Additions. If the original resume contains a link (like a GitHub link in the projects section, a backlink on a certificate in the certifications section, a LinkedIn link, or a portfolio link), you MUST preserve it. Extract the link from the original text (e.g. from markdown link formats like `[Link Text](URL)` or URLs) and output it in the updated resume formatted EXACTLY as HTML tags in your JSON output: <a href="URL" color="blue">Link Text</a>. You must do this for contact headers, project names, and certificates (e.g. <a href="https://example.com/cert" color="blue">AWS Certified Developer</a>). DO NOT strip or drop any URLs or backlinks.
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
      "title": "CERTIFICATIONS (if present)",
      "type": "bullets",
      "content": ["<a href=\"URL\" color=\"blue\">Certificate Name 1</a>", "Certificate Name 2"]
    }},
    {{
      "title": "ACHIEVEMENTS (if present)",
      "type": "bullets",
      "content": ["Achievement 1", "Achievement 2"]
    }}

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
    # Fix common JSON syntax errors caused by unescaped quotes inside values
    import re
    
    # Simple heuristic to escape unescaped double quotes inside values
    # (Matches quotes that are preceded and followed by word characters or spaces, which are likely inside a string)
    cleaned_str = re.sub(r'(?<=[a-zA-Z0-9 ])"(?=[a-zA-Z0-9 ])', r'\"', content_str)
    
    try:
        resume_data = json.loads(content_str, strict=False)
    except json.JSONDecodeError as first_err:
        try:
            resume_data = json.loads(cleaned_str, strict=False)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse PDF JSON: {first_err}\nContent: {content_str}")
            raise first_err
            
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
        # Escape < that doesn't start an allowed tag to prevent ReportLab XML parser errors
        text = re.sub(r'<(?!/?(?:a|font|u|link|b|i|strong|em)\b)', '&lt;', text)
        
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
    left_section_titles = ["PROFESSIONAL SUMMARY", "PROFESSIONAL EXPERIENCE", "EXPERIENCE", "SUMMARY"]
    
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
            # Left column: main content (Summary, Experience, Projects, Training)
            # Right column: sidebar content (Education, Skills, Certs, Achievements, etc.)
            left_titles = {"PROFESSIONAL SUMMARY", "PROFESSIONAL EXPERIENCE",
                           "TRAINING EXPERIENCE", "EXPERIENCE", "SUMMARY", "PROJECTS"}
            if any(lt in title for lt in left_titles):
                left_flowables.extend(section_flowables)
            else:
                right_flowables.extend(section_flowables)
        else:
            story.extend(section_flowables)
    
    if is_two_col:
        # A4 usable width with 10mm margins each side = 190mm ≈ 539pt
        # Left (main): ~62% = 334pt, Right (sidebar): ~38% = 185pt, gutter 20pt between
        LEFT_W = 334
        RIGHT_W = 185
        table_data = [[left_flowables, right_flowables]]
        t = Table(table_data, colWidths=[LEFT_W, RIGHT_W])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (0, 0), 18),   # gutter between columns
            ("LEFTPADDING", (1, 0), (1, 0), 12),     # sidebar indent
            ("LINEAFTER", (0, 0), (0, 0), 0.5, colors.HexColor("#cccccc")),  # divider line
        ]))
        story.append(KeepInFrame(LEFT_W + RIGHT_W, 820, [t], mode="shrink"))
    
    doc.build(story)
    buffer.seek(0)
    return buffer
