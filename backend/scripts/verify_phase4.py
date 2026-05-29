"""
Phase 4 Verification Script

Inserts a test practice_jobs row and a practice_sessions row with status='parsing',
patches api.llm_client.call_openrouter with AsyncMock returning fixture JSON for both
pipeline calls, runs process_session_background directly, then queries the DB to assert:
  - status is 'ready_to_start'
  - resume_parsed, resume_report, generated_questions are populated with schema-valid data

Usage:
    python scripts/verify_phase4.py

Requires the Docker stack to be running (docker-compose up).
"""

import asyncio
import json
import sys
import uuid
from unittest.mock import AsyncMock, patch

import asyncpg

# ---------------------------------------------------------------------------
# Configuration — matches docker-compose / config.py defaults
# ---------------------------------------------------------------------------
DATABASE_URL = "postgresql://practice_user:practice_password_2026@localhost:5434/interview_practice_db"

# ---------------------------------------------------------------------------
# Fixture JSON returned by the mocked call_openrouter
# ---------------------------------------------------------------------------

PIPELINE_1_FIXTURE = json.dumps({
    "personal_info": {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "phone": "+1-555-0100",
        "linkedin": "https://linkedin.com/in/janedoe",
        "github": "https://github.com/janedoe",
        "portfolio": None,
    },
    "summary": "Experienced Python engineer with 5 years building async APIs.",
    "skills": ["Python", "FastAPI", "PostgreSQL", "asyncpg", "Docker"],
    "experience": [
        {
            "title": "Senior Backend Engineer",
            "company": "Acme Corp",
            "duration": "2020–2024",
            "description": "Built high-throughput REST APIs using FastAPI and asyncpg.",
        }
    ],
    "projects": [
        {
            "name": "ResumeParser",
            "description": "Open-source PDF resume parser using PyMuPDF.",
            "link": "https://github.com/janedoe/resumeparser",
        }
    ],
    "education": [
        {
            "degree": "B.Sc. Computer Science",
            "school": "State University",
            "year": "2019",
            "grade": "3.8 GPA",
        }
    ],
    "certifications": [],
})

PIPELINE_2_FIXTURE = json.dumps({
    "resume_report": {
        "score": 82,
        "reference_to_jd": (
            "Jane's background in Python and FastAPI aligns strongly with the role. "
            "Her asyncpg experience directly matches the required database skills."
        ),
        "strengths": [
            "Strong async Python experience",
            "Direct FastAPI and PostgreSQL expertise",
            "Relevant open-source project work",
        ],
        "weaknesses": [
            "No explicit mention of CI/CD pipelines",
            "Limited cloud infrastructure experience",
        ],
    },
    "questions": [
        {
            "id": 1,
            "question": "So, tell me a bit about your background and what brought you to backend engineering.",
            "category": "opening",
            "expected_duration_seconds": 120,
        },
        {
            "id": 2,
            "question": "I noticed you built ResumeParser at Acme Corp — walk me through the architecture decisions you made there.",
            "category": "experience",
            "expected_duration_seconds": 150,
        },
        {
            "id": 3,
            "question": "So you used asyncpg at Acme Corp — what drove that choice over SQLAlchemy async?",
            "category": "experience",
            "expected_duration_seconds": 150,
        },
        {
            "id": 4,
            "question": "I noticed the JD mentions high-throughput systems — how did you approach that at Acme Corp?",
            "category": "rolefit",
            "expected_duration_seconds": 150,
        },
        {
            "id": 5,
            "question": "So when you're designing a new API endpoint, what's your process for thinking about failure modes?",
            "category": "situational",
            "expected_duration_seconds": 150,
        },
        {
            "id": 6,
            "question": "I noticed Docker is in your skills — how have you used it to manage local dev environments on past projects?",
            "category": "rolefit",
            "expected_duration_seconds": 150,
        },
        {
            "id": 7,
            "question": "So looking back at your time at Acme Corp, what's the biggest technical shift you navigated and what did it teach you?",
            "category": "behavioral",
            "expected_duration_seconds": 120,
        },
        {
            "id": 8,
            "question": "I noticed you've been focused on backend systems — where do you see yourself growing from here?",
            "category": "closing",
            "expected_duration_seconds": 120,
        },
    ],
})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _section(title: str) -> None:
    print(f"\n{'='*60}")
    print(title)
    print(f"{'='*60}")


def _pass(msg: str) -> None:
    print(f"[PASS] {msg}")


def _fail(msg: str) -> None:
    print(f"[FAIL] {msg}")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Main verification coroutine
# ---------------------------------------------------------------------------

async def main() -> None:
    from schemas.questions import QuestionArraySchema
    from schemas.resume import ResumeParsedData, ResumeReportData
    from services.background_pipeline import process_session_background

    session_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    # file_path is irrelevant — extract_resume_text is also mocked via call_openrouter patch
    file_path = f"./storage/resumes/{session_id}/resume.pdf"

    conn = await asyncpg.connect(DATABASE_URL)

    # -----------------------------------------------------------------------
    # Step 1: Insert test rows
    # -----------------------------------------------------------------------
    _section("STEP 1: Inserting test rows into the database")

    try:
        await conn.execute(
            """
            INSERT INTO practice_jobs (id, title, description)
            VALUES ($1, $2, $3)
            """,
            job_id,
            "Test Job — Phase 4 Verification",
            "Seeking a Python/FastAPI engineer with async and PostgreSQL experience.",
        )
        _pass(f"practice_jobs row inserted — job_id={job_id}")

        await conn.execute(
            """
            INSERT INTO practice_sessions (id, job_id, status, resume_url)
            VALUES ($1, $2, 'parsing', $3)
            """,
            session_id,
            job_id,
            file_path,
        )
        _pass(f"practice_sessions row inserted — session_id={session_id}, status='parsing'")
    except Exception as exc:
        _fail(f"DB insert failed: {exc}")

    # -----------------------------------------------------------------------
    # Step 2: Build a minimal asyncpg pool mock pointing at the real DB
    # -----------------------------------------------------------------------
    _section("STEP 2: Running process_session_background with mocked LLM calls")

    # We use a real asyncpg pool so DB writes are exercised against the real database.
    db_pool = await asyncpg.create_pool(DATABASE_URL)

    # call_openrouter is called twice: once for Pipeline 1, once for Pipeline 2.
    # We also need to mock extract_resume_text since there's no real PDF on disk.
    pipeline_responses = [PIPELINE_1_FIXTURE, PIPELINE_2_FIXTURE]
    mock_call = AsyncMock(side_effect=pipeline_responses)

    try:
        with patch("services.background_pipeline.call_openrouter", mock_call), \
             patch("services.background_pipeline.extract_resume_text", AsyncMock(return_value="Fake resume text")):
            await process_session_background(session_id, job_id, file_path, db_pool)
        _pass("process_session_background completed without raising an exception")
    except Exception as exc:
        _fail(f"process_session_background raised unexpectedly: {exc}")
    finally:
        await db_pool.close()

    # -----------------------------------------------------------------------
    # Step 3: Assert DB state
    # -----------------------------------------------------------------------
    _section("STEP 3: Asserting final database state")

    row = await conn.fetchrow(
        "SELECT status, resume_parsed, resume_report, generated_questions FROM practice_sessions WHERE id=$1",
        session_id,
    )

    if row is None:
        _fail(f"practice_sessions row not found for session_id={session_id}")

    # 3a. Status transition
    if row["status"] != "ready_to_start":
        _fail(f"Expected status='ready_to_start', got '{row['status']}'")
    _pass("status is 'ready_to_start'")

    # 3b. resume_parsed — validate against ResumeParsedData
    if row["resume_parsed"] is None:
        _fail("resume_parsed is NULL")
    try:
        parsed = ResumeParsedData.model_validate_json(row["resume_parsed"])
        _pass(f"resume_parsed is valid ResumeParsedData (name={parsed.personal_info.name})")
    except Exception as exc:
        _fail(f"resume_parsed failed schema validation: {exc}")

    # 3c. resume_report — validate against ResumeReportData
    if row["resume_report"] is None:
        _fail("resume_report is NULL")
    try:
        report = ResumeReportData.model_validate_json(row["resume_report"])
        if not (0 <= report.score <= 100):
            _fail(f"resume_report.score out of range: {report.score}")
        _pass(f"resume_report is valid ResumeReportData (score={report.score})")
    except Exception as exc:
        _fail(f"resume_report failed schema validation: {exc}")

    # 3d. generated_questions — validate against QuestionArraySchema
    if row["generated_questions"] is None:
        _fail("generated_questions is NULL")
    try:
        qs = QuestionArraySchema.model_validate_json(row["generated_questions"])
        if len(qs.questions) != 8:
            _fail(f"Expected 8 questions, got {len(qs.questions)}")
        _pass(f"generated_questions is valid QuestionArraySchema (count={len(qs.questions)})")
    except Exception as exc:
        _fail(f"generated_questions failed schema validation: {exc}")

    # -----------------------------------------------------------------------
    # Step 4: Cleanup
    # -----------------------------------------------------------------------
    _section("STEP 4: Cleaning up test rows")
    await conn.execute("DELETE FROM practice_sessions WHERE id=$1", session_id)
    await conn.execute("DELETE FROM practice_jobs WHERE id=$1", job_id)
    await conn.close()
    _pass("Test rows removed")

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print(f"\n{'='*60}")
    print("Phase 4 verification PASSED.")
    print(f"  session_id : {session_id}")
    print(f"  job_id     : {job_id}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
