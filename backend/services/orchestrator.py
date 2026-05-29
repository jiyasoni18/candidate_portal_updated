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
import asyncio

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
    pre_extracted_resume_text: str = "",
    pre_extracted_jd_text: str = "",
) -> None:
    """Run the full pre-interview pipeline for a newly created practice session.

    Any unhandled exception is caught and logged so the FastAPI worker is never crashed.
    """
    try:
        # Stage 1 — Use pre-extracted text if available (avoids re-reading the file)
        logger.info("Pipeline starting — session_id=%s", session_id)
        if pre_extracted_resume_text:
            raw_text = pre_extracted_resume_text
            logger.info("Using pre-extracted resume text (%d chars) — session_id=%s", len(raw_text), session_id)
        else:
            raw_text = await extract_resume_text(file_path)
            logger.info("Text extracted (%d chars) — session_id=%s", len(raw_text), session_id)

        # Use pre-extracted JD text if available (avoids a DB round-trip)
        if pre_extracted_jd_text:
            jd_text: str = pre_extracted_jd_text
        else:
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
            jd_text = row["description"]

        # Start the enhanced analysis concurrently since it only needs raw_text and jd_text
        enhanced_analysis_task = asyncio.create_task(
            analyze_resume_enhanced(
                raw_text,
                jd_text,
                api_key=settings.OPENROUTER_API_KEY,
            )
        )

        # Stage 2 & 3 — Concurrently parse resume and score against JD
        async def _run_parse():
            parsed = await parse_resume(raw_text)
            async with db_pool.acquire() as conn:
                await conn.execute(
                    "UPDATE practice_sessions SET resume_parsed=$1, status='scoring' WHERE id=$2",
                    parsed.model_dump_json(),
                    session_id,
                )
            return parsed

        async def _run_analysis():
            return await analyse_resume_against_jd(raw_text, jd_text)

        # Run parse and analysis concurrently
        parse_task = asyncio.create_task(_run_parse())
        analysis_task = asyncio.create_task(_run_analysis())

        parsed_resume = await parse_task
        logger.info("Resume parsed — session_id=%s", session_id)

        report, questions = await analysis_task
        logger.info("Resume analysis complete — session_id=%s", session_id)

        # Stage 4 — Await the enhanced analysis that was running in the background
        enhanced_analysis = None
        try:
            enhanced_analysis = await enhanced_analysis_task
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
