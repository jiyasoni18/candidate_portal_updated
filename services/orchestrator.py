"""
orchestrator.py
---------------
Ties all pipeline stages together into a single background task.

Flow for a new practice session:
  1. document_extraction  — PDF → raw text
  2. resume_parser        — raw text → structured ResumeParsedData  (DB: status='scoring')
  3. resume_analysis      — ResumeParsedData + JD → ResumeReportData + 8 questions
                                                                      (DB: status='ready_to_start')

The grading pipeline (interview_grader.py) runs separately after the interview ends.
"""
import json
import logging

from services.document_extraction import extract_resume_text
from services.resume_parser import parse_resume
from services.resume_analysis import analyse_resume_against_jd
from services.enhanced_analyzer import analyze_resume_enhanced
from config import settings

logger = logging.getLogger(__name__)


async def process_session_background(
    session_id: str,
    job_id: str,
    file_path: str,
    db_pool,  # asyncpg Pool passed from app.state
) -> None:
    """Run the full pre-interview pipeline for a newly created practice session.

    Any unhandled exception is caught and logged so the FastAPI worker is never crashed.
    """
    try:
        # Stage 1 — Extract raw text from the uploaded PDF
        logger.info("Pipeline starting — session_id=%s", session_id)
        raw_text = await extract_resume_text(file_path)
        logger.info("Text extracted (%d chars) — session_id=%s", len(raw_text), session_id)

        # Stage 2 — Parse the resume into structured data
        parsed_resume = await parse_resume(raw_text)
        logger.info("Resume parsed — session_id=%s", session_id)

        async with db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE practice_sessions SET resume_parsed=$1, status='scoring' WHERE id=$2",
                parsed_resume.model_dump_json(),
                session_id,
            )
        logger.info("DB updated to 'scoring' — session_id=%s", session_id)

        # Fetch the job description text needed for Stage 3
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT description FROM practice_jobs WHERE id=$1",
                job_id,
            )
        if row is None:
            logger.error(
                "practice_jobs row not found — job_id=%s session_id=%s", job_id, session_id
            )
            return
        jd_text: str = row["description"]

        # Stage 3 — Score resume against JD and generate interview questions
        report, questions = await analyse_resume_against_jd(parsed_resume, jd_text)
        logger.info("Resume analysis complete — session_id=%s", session_id)

        # Stage 4 — Run enhanced analysis (non-blocking, with fallback)
        enhanced_analysis = None
        try:
            enhanced_analysis = await analyze_resume_enhanced(
                raw_text,
                jd_text,
                api_key=settings.OPENROUTER_API_KEY,
            )
            logger.info("Enhanced analysis complete — session_id=%s", session_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Enhanced analysis failed — session_id=%s error=%s (falling back to basic analysis)",
                session_id,
                exc,
            )

        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE practice_sessions
                SET resume_report=$1, generated_questions=$2, enhanced_analysis=$3, status='ready_to_start'
                WHERE id=$4
                """,
                report.model_dump_json(),
                questions.model_dump_json(),
                json.dumps(enhanced_analysis) if enhanced_analysis else None,
                session_id,
            )
        logger.info("DB updated to 'ready_to_start' — session_id=%s", session_id)

    except Exception as exc:  # noqa: BLE001
        logger.error(
            "process_session_background failed — session_id=%s error=%s",
            session_id,
            exc,
            exc_info=True,
        )
