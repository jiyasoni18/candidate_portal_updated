"""
Phase 3 Verification Script

Posts sample_resume.pdf to the running /api/v1/practice/initialize endpoint,
prints the response, then queries the DB to confirm the practice_jobs and
practice_sessions rows exist with the expected values.

Usage:
    python scripts/verify_phase3.py

Requires the Docker stack to be running (docker-compose up).
"""

import asyncio
import os
import sys

import asyncpg
import httpx

# ---------------------------------------------------------------------------
# Configuration — matches docker-compose / config.py defaults
# ---------------------------------------------------------------------------
BASE_URL = "http://localhost:8001"
DATABASE_URL = "postgresql://practice_user:practice_password_2026@localhost:5434/interview_practice_db"
SAMPLE_RESUME_PATH = os.path.join(os.path.dirname(__file__), "..", "sample_resume.pdf")
JD_TEXT = (
    "Seeking a Software Engineer experienced in Python and FastAPI. "
    "The ideal candidate has strong async programming skills and PostgreSQL experience."
)


# ---------------------------------------------------------------------------
# Step 1: POST to the initialization endpoint
# ---------------------------------------------------------------------------
def post_initialize() -> dict:
    resume_path = os.path.abspath(SAMPLE_RESUME_PATH)
    if not os.path.exists(resume_path):
        print(f"[ERROR] sample_resume.pdf not found at: {resume_path}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print("STEP 1: Posting to /api/v1/practice/initialize")
    print(f"{'='*60}")

    with open(resume_path, "rb") as f:
        response = httpx.post(
            f"{BASE_URL}/api/v1/practice/initialize",
            files={"file": ("sample_resume.pdf", f, "application/pdf")},
            data={"jd_text": JD_TEXT},
            timeout=10.0,
        )

    print(f"Status Code : {response.status_code}")
    print(f"Response    : {response.text}")

    if response.status_code != 201:
        print(f"\n[FAIL] Expected HTTP 201, got {response.status_code}")
        sys.exit(1)

    body = response.json()
    required_keys = {"session_id", "job_id", "status", "message"}
    missing = required_keys - body.keys()
    if missing:
        print(f"\n[FAIL] Response missing keys: {missing}")
        sys.exit(1)

    if body["status"] != "parsing":
        print(f"\n[FAIL] Expected status='parsing', got '{body['status']}'")
        sys.exit(1)

    print("\n[PASS] HTTP 201 received with correct response shape.")
    return body


# ---------------------------------------------------------------------------
# Step 2: Query the DB to confirm rows exist
# ---------------------------------------------------------------------------
async def verify_db(session_id: str, job_id: str) -> None:
    print(f"\n{'='*60}")
    print("STEP 2: Verifying database rows")
    print(f"{'='*60}")

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Verify practice_jobs row
        job_row = await conn.fetchrow(
            "SELECT id, title, description FROM practice_jobs WHERE id = $1",
            job_id,
        )
        if job_row is None:
            print(f"[FAIL] No practice_jobs row found for job_id={job_id}")
            sys.exit(1)

        print(f"practice_jobs row found:")
        print(f"  id          : {job_row['id']}")
        print(f"  title       : {job_row['title']}")
        print(f"  description : {job_row['description'][:60]}...")
        print("[PASS] practice_jobs row verified.")

        # Verify practice_sessions row
        session_row = await conn.fetchrow(
            "SELECT id, job_id, status, resume_url FROM practice_sessions WHERE id = $1",
            session_id,
        )
        if session_row is None:
            print(f"\n[FAIL] No practice_sessions row found for session_id={session_id}")
            sys.exit(1)

        print(f"\npractice_sessions row found:")
        print(f"  id         : {session_row['id']}")
        print(f"  job_id     : {session_row['job_id']}")
        print(f"  status     : {session_row['status']}")
        print(f"  resume_url : {session_row['resume_url']}")

        if str(session_row["job_id"]) != job_id:
            print(f"[FAIL] session job_id mismatch: expected {job_id}, got {session_row['job_id']}")
            sys.exit(1)

        if session_row["status"] != "parsing":
            print(f"[FAIL] Expected status='parsing', got '{session_row['status']}'")
            sys.exit(1)

        expected_resume_url = f"./storage/resumes/{session_id}/resume.pdf"
        if session_row["resume_url"] != expected_resume_url:
            print(f"[FAIL] resume_url mismatch: expected '{expected_resume_url}', got '{session_row['resume_url']}'")
            sys.exit(1)

        print("[PASS] practice_sessions row verified.")

    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main() -> None:
    response_body = post_initialize()
    session_id = response_body["session_id"]
    job_id = response_body["job_id"]

    await verify_db(session_id, job_id)

    print(f"\n{'='*60}")
    print("Phase 3 verification PASSED.")
    print(f"  session_id : {session_id}")
    print(f"  job_id     : {job_id}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
