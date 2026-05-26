"""
resume_analysis.py
------------------
Pipeline 2 — two separate LLM calls:
  A) Resume report (score, strengths, weaknesses) — unchanged
  B) Question generation — uses QUESTION_GEN_PROMPT from question_gen.py

Input:  ResumeParsedData + JD text (str)
Output: (ResumeReportData, QuestionArraySchema)
"""
import json
import logging

from api.llm_client import call_openrouter
from question_gen import QUESTION_GEN_PROMPT
from schemas.questions import QuestionArraySchema
from schemas.resume import ResumeParsedData, ResumeReportData

logger = logging.getLogger(__name__)


# ── Part A: resume report prompt (unchanged) ──────────────────────────────────

def _build_prompt() -> str:  # kept for background_pipeline shim compatibility
    return (
        "You are an expert technical interviewer and resume analyst.\n"
        'You will receive a JSON object with two keys: "resume" (parsed resume data) '
        'and "jd_text" (job description text).\n\n'
        'Return ONLY a valid JSON object with exactly one top-level key: '
        '"resume_report". No markdown, no extra keys.\n\n'
        '"resume_report" must match this structure:\n'
        "{\n"
        '  "score": <integer 0-100 representing resume-to-JD alignment>,\n'
        '  "reference_to_jd": "<one paragraph summarising alignment with the JD>",\n'
        '  "strengths": ["<strength>", ...],\n'
        '  "weaknesses": ["<weakness>", ...]\n'
        "}\n"
    )


# ── Part B: question generation ───────────────────────────────────────────────

def _build_question_prompt(parsed_resume: ResumeParsedData, jd_text: str) -> str:
    """Format QUESTION_GEN_PROMPT with available data."""
    # Extract candidate name from parsed resume if available
    name = parsed_resume.personal_info.name or "there"

    # Evaluation parameters derived from the JD — passed as a plain summary
    evaluation_parameters = (
        "communication clarity, relevant experience depth, role motivation, "
        "career trajectory, cultural fit"
    )

    return QUESTION_GEN_PROMPT.format(
        resume=json.dumps(parsed_resume.model_dump(), indent=2),
        jd=jd_text,
        evaluation_parameters=evaluation_parameters,
        name=name,
    )


# ── Combined pipeline entry point ─────────────────────────────────────────────

async def analyse_resume_against_jd(
    parsed_resume: ResumeParsedData,
    jd_text: str,
) -> tuple[ResumeReportData, QuestionArraySchema]:
    """Score the resume against the JD and generate 8 interview questions.

    Two separate LLM calls:
      1. Resume report (score + strengths/weaknesses)
      2. Question generation using QUESTION_GEN_PROMPT
    """
    import asyncio

    async def _get_report() -> ResumeReportData:
        user_content = json.dumps({
            "resume": parsed_resume.model_dump(),
            "jd_text": jd_text,
        })
        raw_json = await call_openrouter(_build_prompt(), user_content)
        data = json.loads(raw_json)
        return ResumeReportData.model_validate(data["resume_report"])

    async def _get_questions() -> QuestionArraySchema:
        prompt = _build_question_prompt(parsed_resume, jd_text)
        # QUESTION_GEN_PROMPT is a user-only prompt — pass as user content with empty system
        raw_json = await call_openrouter("", prompt)
        data = json.loads(raw_json)
        return QuestionArraySchema.model_validate({"questions": data["questions"]})

    report, questions = await asyncio.gather(_get_report(), _get_questions())
    return report, questions
