"""
interview_grader.py
-------------------
Pipeline 3 (entry point) — fetches session data from the DB, calls the LLM
via assessment_scoring.py, applies server-side math, and persists the result.

This is the async background task that runs after an interview session ends.
"""
import json
import logging

from api.llm_client import call_openrouter
from config import settings
from schemas.assessment import InterviewAssessmentSchema
from services.assessment_scoring import (
    build_grading_prompt,
    compute_final_score,
    count_candidate_turns,
    map_verdict,
)

logger = logging.getLogger(__name__)


async def grade_session_background(session_id: str, db_pool) -> None:
    """Evaluate a completed interview transcript and persist the assessment to the DB.

    Steps:
      1. Fetch transcript + resume + job_id from practice_sessions
      2. Fetch JD text from practice_jobs
      3. Compute completion_ratio from candidate turn count
      4. Call LLM with grading prompt
      5. Apply weighted scoring math server-side
      6. Persist InterviewAssessmentSchema + status='completed' to DB
    """
    try:
        # 1. Fetch session data
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
            json.loads(row["transcript"])
            if isinstance(row["transcript"], str)
            else row["transcript"]
        )
        resume_parsed = (
            json.loads(row["resume_parsed"])
            if isinstance(row["resume_parsed"], str)
            else row["resume_parsed"]
        )
        job_id = row["job_id"]

        # 2. Fetch JD text
        async with db_pool.acquire() as conn:
            job_row = await conn.fetchrow(
                "SELECT description FROM practice_jobs WHERE id=$1", job_id
            )
        if job_row is None:
            logger.error(
                "grade_session: practice_jobs row not found — job_id=%s session_id=%s",
                job_id,
                session_id,
            )
            return
        jd_text: str = job_row["description"]

        # 3. Compute completion ratio (candidate turns / 8 questions)
        questions_answered = count_candidate_turns(transcript)
        completion_ratio = min(questions_answered / 8, 1.0)

        # 4. Call LLM
        system_prompt, user_content = build_grading_prompt(jd_text, resume_parsed, transcript)
        raw_json = await call_openrouter(system_prompt, user_content, model=settings.GRADING_MODEL)

        # 5. Validate LLM response and apply server-side scoring
        assessment = InterviewAssessmentSchema.model_validate_json(raw_json)
        final_score = compute_final_score(assessment.dimension_scores, completion_ratio)
        verdict = map_verdict(final_score)

        assessment = assessment.model_copy(update={
            "overall_score": final_score,
            "completion_ratio": completion_ratio,
            "practice_verdict": verdict,
            "turns_analyzed": len(transcript),
        })

        # 6. Persist to DB
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
            session_id,
            final_score,
            verdict,
        )

    except Exception as exc:  # noqa: BLE001
        logger.error(
            "grade_session_background failed — session_id=%s error=%s",
            session_id,
            exc,
            exc_info=True,
        )
