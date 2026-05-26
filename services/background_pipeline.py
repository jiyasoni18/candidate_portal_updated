"""
background_pipeline.py
----------------------
Backwards-compatibility shim + thin wrappers.

All logic has been split into focused modules:

  services/
  ├── document_extraction.py  — PDF → raw text
  ├── resume_parser.py        — raw text → structured resume data
  ├── resume_analysis.py      — resume + JD → alignment score + interview questions
  ├── assessment_scoring.py   — grading prompt builder + scoring math + verdict mapping
  ├── interview_grader.py     — post-interview grading background task
  └── orchestrator.py         — pre-interview pipeline (stages 1-3)

IMPORTANT — patch compatibility:
  Tests and scripts patch "services.background_pipeline.call_openrouter" and
  "services.background_pipeline.extract_resume_text".  For unittest.mock.patch
  to intercept those names, they must be real attributes on THIS module and the
  wrapper functions below must call them via the module-local name (not via the
  sub-module's own reference).  That is why run_pipeline_1, run_pipeline_2, and
  extract_resume_text are re-implemented as thin wrappers here rather than
  simple re-exports.
"""
import json
import logging

# These names are imported here so that patch("services.background_pipeline.X")
# works correctly in tests and scripts.
from api.llm_client import call_openrouter  # noqa: F401  — patchable target
from services.document_extraction import extract_resume_text  # noqa: F401  — patchable target

from services.resume_parser import _build_prompt as _resume_parser_prompt
from services.resume_analysis import _build_prompt as _analysis_prompt
from schemas.questions import QuestionArraySchema
from schemas.resume import ResumeParsedData, ResumeReportData

# Re-exports used by callers that don't need patching
from services.orchestrator import process_session_background
from services.assessment_scoring import (
    build_grading_prompt,
    compute_final_score,
    count_candidate_turns,
    map_verdict,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Wrapper functions — call the module-local call_openrouter so patches work
# ---------------------------------------------------------------------------

async def grade_session_background(session_id: str, db_pool) -> None:
    """Post-interview grading pipeline — wrapper so patches on call_openrouter work."""
    import json as _json
    from schemas.assessment import InterviewAssessmentSchema
    from config import settings

    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT transcript, resume_parsed, job_id FROM practice_sessions WHERE id=$1",
                session_id,
            )
        if row is None or row["transcript"] is None:
            logger.error(
                "grade_session: session not found or transcript null — session_id=%s", session_id
            )
            return

        transcript = (
            _json.loads(row["transcript"])
            if isinstance(row["transcript"], str)
            else row["transcript"]
        )
        resume_parsed = (
            _json.loads(row["resume_parsed"])
            if isinstance(row["resume_parsed"], str)
            else row["resume_parsed"]
        )
        job_id = row["job_id"]

        async with db_pool.acquire() as conn:
            job_row = await conn.fetchrow(
                "SELECT description FROM practice_jobs WHERE id=$1", job_id
            )
        if job_row is None:
            logger.error(
                "grade_session: practice_jobs row not found — job_id=%s session_id=%s",
                job_id, session_id,
            )
            return
        jd_text: str = job_row["description"]

        questions_answered = count_candidate_turns(transcript)
        completion_ratio = min(questions_answered / 8, 1.0)

        # Short-circuit: candidate said nothing — skip LLM, write zero-score result
        if questions_answered == 0:
            zero_dim = {
                "score": 0, "max_score": 100, "verdict": "Weak",
                "evidence": "Candidate did not speak during this session.",
                "strengths": [], "gaps": [],
            }
            assessment = InterviewAssessmentSchema.model_validate({
                "overall_score": 0,
                "practice_verdict": map_verdict(0),
                "hire_recommendation": "Strong No",
                "summary": (
                    "The candidate did not speak during this practice session. "
                    "No evaluation is possible. Please attempt the interview again and "
                    "ensure your microphone is working before starting."
                ),
                "dimension_scores": {
                    "technical":      {**zero_dim, "label": "Technical Familiarity"},
                    "role_alignment": {**zero_dim, "label": "Role Alignment"},
                    "communication":  {**zero_dim, "label": "Communication Skills"},
                    "presence":       {**zero_dim, "label": "Presence & Engagement"},
                },
                "overall_strengths": [],
                "overall_gaps": ["No responses were recorded — the session was silent."],
                "red_flags": ["Candidate produced zero spoken turns."],
                "technical_round_probes": [
                    "Walk me through your most recent project end-to-end.",
                    "How does your background align with this role's core requirements?",
                    "Describe a technical challenge you solved and how you approached it.",
                ],
                "advance_to_technical": False,
                "advance_reasoning": "No candidate responses were recorded in this session.",
                "candidate_level": "unknown",
                "interview_quality": "incomplete",
                "turns_analyzed": len(transcript),
                "completion_ratio": 0.0,
            })
            async with db_pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE practice_sessions
                    SET interview_assessment=$1, status='completed'
                    WHERE id=$2
                    """,
                    assessment.model_dump_json(),
                    session_id,
                )
            logger.info("Silent session — zero-score result written — session_id=%s", session_id)
            return

        system_prompt, user_content = build_grading_prompt(jd_text, resume_parsed, transcript)
        raw_json = await call_openrouter(system_prompt, user_content, model=settings.GRADING_MODEL)

        assessment = InterviewAssessmentSchema.model_validate_json(raw_json)
        final_score = compute_final_score(assessment.dimension_scores, completion_ratio)
        verdict = map_verdict(final_score)

        assessment = assessment.model_copy(update={
            "overall_score": final_score,
            "completion_ratio": completion_ratio,
            "practice_verdict": verdict,
            "turns_analyzed": len(transcript),
        })

        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE practice_sessions
                SET interview_assessment=$1, status='completed'
                WHERE id=$2
                """,
                assessment.model_dump_json(),
                session_id,
            )
        logger.info(
            "Grading complete — session_id=%s score=%d verdict=%s",
            session_id, final_score, verdict,
        )

    except Exception as exc:  # noqa: BLE001
        logger.error(
            "grade_session_background failed — session_id=%s error=%s",
            session_id, exc, exc_info=True,
        )
        # Mark the session so the frontend stops polling instead of spinning forever
        try:
            async with db_pool.acquire() as conn:
                await conn.execute(
                    "UPDATE practice_sessions SET status='grading_failed' WHERE id=$1",
                    session_id,
                )
        except Exception:  # noqa: BLE001
            pass


async def run_pipeline_1(raw_text: str) -> ResumeParsedData:
    """Parse raw resume text into a structured ResumeParsedData object."""
    raw_json = await call_openrouter(_resume_parser_prompt(), raw_text)
    return ResumeParsedData.model_validate_json(raw_json)


async def run_pipeline_2(
    parsed_resume: ResumeParsedData,
    jd_text: str,
) -> tuple[ResumeReportData, QuestionArraySchema]:
    """Score the resume against the JD and generate 8 interview questions."""
    user_content = json.dumps({
        "resume": parsed_resume.model_dump(),
        "jd_text": jd_text,
    })
    raw_json = await call_openrouter(_analysis_prompt(), user_content)
    data = json.loads(raw_json)
    report = ResumeReportData.model_validate(data["resume_report"])
    questions = QuestionArraySchema.model_validate({"questions": data["questions"]})
    return report, questions


__all__ = [
    "call_openrouter",
    "extract_resume_text",
    "run_pipeline_1",
    "run_pipeline_2",
    "process_session_background",
    "grade_session_background",
    "build_grading_prompt",
    "compute_final_score",
    "count_candidate_turns",
    "map_verdict",
]
