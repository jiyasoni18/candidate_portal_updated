"""
Phase 5 Verification Script

Seeds a test practice_jobs + practice_sessions row with status='ready_to_start'
and a mock resume_report payload, then uses httpx.AsyncClient with ASGITransport
to call both Phase 5 endpoints without a live server. Asserts:

  - GET /api/v1/practice/sessions returns 200 with resume_score populated
  - GET /api/v1/practice/session/{seeded_id} returns 200 with resume_report populated
  - GET /api/v1/practice/session/{random_uuid} returns 404

Cleans up seeded rows after assertions.

Usage:
    python scripts/verify_phase5.py

Requires the Docker stack to be running (docker-compose up).
"""

import asyncio
import json
import sys
import uuid

import asyncpg
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from main import app

# ---------------------------------------------------------------------------
# Configuration — matches docker-compose / config.py defaults
# ---------------------------------------------------------------------------
DATABASE_URL = "postgresql://practice_user:practice_password_2026@localhost:5434/interview_practice_db"

MOCK_USER_ID = "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d"

MOCK_RESUME_REPORT = {
    "score": 78,
    "reference_to_jd": "Strong alignment with the Python/FastAPI requirements.",
    "strengths": ["Async Python expertise", "PostgreSQL experience"],
    "weaknesses": ["Limited CI/CD exposure"],
}


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
    session_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())

    conn = await asyncpg.connect(DATABASE_URL)

    # -----------------------------------------------------------------------
    # Step 1: Seed test rows
    # -----------------------------------------------------------------------
    _section("STEP 1: Seeding test rows into the database")

    try:
        await conn.execute(
            """
            INSERT INTO practice_jobs (id, user_id, title, description)
            VALUES ($1, $2, $3, $4)
            """,
            job_id,
            MOCK_USER_ID,
            "Test Job — Phase 5 Verification",
            "Seeking a Python/FastAPI engineer with async and PostgreSQL experience.",
        )
        _pass(f"practice_jobs row inserted — job_id={job_id}")

        await conn.execute(
            """
            INSERT INTO practice_sessions (id, user_id, job_id, status, resume_url, resume_report)
            VALUES ($1, $2, $3, 'ready_to_start', $4, $5)
            """,
            session_id,
            MOCK_USER_ID,
            job_id,
            f"./storage/resumes/{session_id}/resume.pdf",
            json.dumps(MOCK_RESUME_REPORT),
        )
        _pass(f"practice_sessions row inserted — session_id={session_id}, status='ready_to_start'")
    except Exception as exc:
        await conn.close()
        _fail(f"DB seed failed: {exc}")

    # -----------------------------------------------------------------------
    # Step 2: Call endpoints via ASGITransport (no live server needed)
    # -----------------------------------------------------------------------
    _section("STEP 2: Calling Phase 5 endpoints via ASGITransport")

    try:
        async with LifespanManager(app) as manager:
            async with AsyncClient(
                transport=ASGITransport(app=manager.app),
                base_url="http://test",
            ) as client:

                # --- 2a. List endpoint ---
                list_resp = await client.get("/api/v1/practice/sessions")
                if list_resp.status_code != 200:
                    _fail(f"GET /sessions returned {list_resp.status_code}, expected 200")
                _pass(f"GET /sessions returned 200")

                sessions = list_resp.json()
                if not isinstance(sessions, list) or len(sessions) == 0:
                    _fail("GET /sessions returned empty list — seeded session not found")

                seeded = next((s for s in sessions if s["session_id"] == session_id), None)
                if seeded is None:
                    _fail(f"Seeded session_id={session_id} not found in list response")

                if seeded.get("resume_score") != MOCK_RESUME_REPORT["score"]:
                    _fail(
                        f"Expected resume_score={MOCK_RESUME_REPORT['score']}, "
                        f"got {seeded.get('resume_score')}"
                    )
                _pass(f"resume_score={seeded['resume_score']} correctly extracted from resume_report")

                # --- 2b. Detail endpoint — seeded session ---
                detail_resp = await client.get(f"/api/v1/practice/session/{session_id}")
                if detail_resp.status_code != 200:
                    _fail(f"GET /session/{{id}} returned {detail_resp.status_code}, expected 200")
                _pass(f"GET /session/{session_id} returned 200")

                detail = detail_resp.json()
                if detail.get("resume_report") is None:
                    _fail("resume_report is null in detail response — expected full payload")
                if detail["resume_report"].get("score") != MOCK_RESUME_REPORT["score"]:
                    _fail(
                        f"resume_report.score mismatch: expected {MOCK_RESUME_REPORT['score']}, "
                        f"got {detail['resume_report'].get('score')}"
                    )
                _pass(f"resume_report populated correctly (score={detail['resume_report']['score']})")

                # --- 2c. Detail endpoint — random UUID → 404 ---
                random_id = str(uuid.uuid4())
                not_found_resp = await client.get(f"/api/v1/practice/session/{random_id}")
                if not_found_resp.status_code != 404:
                    _fail(
                        f"GET /session/{{random_uuid}} returned {not_found_resp.status_code}, "
                        f"expected 404"
                    )
                _pass(f"GET /session/{random_id} correctly returned 404")

    except SystemExit:
        raise
    except Exception as exc:
        _fail(f"Unexpected error during endpoint calls: {exc}")

    # -----------------------------------------------------------------------
    # Step 3: Cleanup
    # -----------------------------------------------------------------------
    _section("STEP 3: Cleaning up seeded rows")

    try:
        await conn.execute("DELETE FROM practice_sessions WHERE id = $1", session_id)
        await conn.execute("DELETE FROM practice_jobs WHERE id = $1", job_id)
        _pass("Seeded rows removed")
    except Exception as exc:
        print(f"[WARN] Cleanup failed: {exc}")
    finally:
        await conn.close()

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print(f"\n{'='*60}")
    print("Phase 5 verification PASSED.")
    print(f"  session_id : {session_id}")
    print(f"  job_id     : {job_id}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
