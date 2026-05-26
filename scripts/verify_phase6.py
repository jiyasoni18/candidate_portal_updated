"""
Phase 6 Verification Script

Seeds a test user (if needed), practice_jobs, and practice_sessions row with
status='ready_to_start' and mock generated_questions + resume_report, then uses
httpx.AsyncClient with ASGITransport to call the Phase 6 start endpoint without
a live LiveKit server (provision_room and generate_token are patched).

Asserts:
  - POST /api/v1/practice/session/{session_id}/start returns 201 with correct shape
  - JWT payload contains correct `room` and `sub` (identity) claims
  - DB row has status='interviewing' and livekit_room_name='practice-room-{session_id}'
  - Calling the same endpoint again returns HTTP 400 (idempotency guard)

Cleans up seeded rows after assertions.

Usage:
    python scripts/verify_phase6.py

Requires the Docker stack to be running (docker-compose up).
"""

import asyncio
import base64
import json
import sys
import uuid
from unittest.mock import AsyncMock, patch

import asyncpg
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from main import app

# ---------------------------------------------------------------------------
# Configuration — matches docker-compose / config.py defaults
# ---------------------------------------------------------------------------
DATABASE_URL = "postgresql://practice_user:practice_password_2026@localhost:5434/interview_practice_db"

# Seeded test user from database/init.sql
MOCK_USER_ID = "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d"

MOCK_QUESTIONS = [
    {
        "id": 1,
        "question": "Tell me about your background.",
        "category": "opening",
        "expected_duration_seconds": 120,
    }
]

MOCK_RESUME_REPORT = {
    "score": 82,
    "reference_to_jd": "Strong alignment with Python/FastAPI requirements.",
    "strengths": ["Async Python", "PostgreSQL"],
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


def _decode_jwt_payload(token: str) -> dict:
    """Decode JWT payload without signature verification."""
    parts = token.split(".")
    if len(parts) != 3:
        _fail(f"Invalid JWT format — expected 3 parts, got {len(parts)}")
    # Add padding if needed
    payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
    payload_bytes = base64.urlsafe_b64decode(payload_b64)
    return json.loads(payload_bytes)


# ---------------------------------------------------------------------------
# Main verification coroutine
# ---------------------------------------------------------------------------

async def main() -> None:
    session_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    room_name = f"practice-room-{session_id}"

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
            "Test Job — Phase 6 Verification",
            "Seeking a Python/FastAPI engineer with async and PostgreSQL experience.",
        )
        _pass(f"practice_jobs row inserted — job_id={job_id}")

        await conn.execute(
            """
            INSERT INTO practice_sessions (
                id, user_id, job_id, status, resume_url,
                resume_report, generated_questions
            )
            VALUES ($1, $2, $3, 'ready_to_start', $4, $5, $6)
            """,
            session_id,
            MOCK_USER_ID,
            job_id,
            f"./storage/resumes/{session_id}/resume.pdf",
            json.dumps(MOCK_RESUME_REPORT),
            json.dumps(MOCK_QUESTIONS),
        )
        _pass(
            f"practice_sessions row inserted — session_id={session_id}, "
            f"status='ready_to_start'"
        )
    except Exception as exc:
        await conn.close()
        _fail(f"DB seed failed: {exc}")

    # -----------------------------------------------------------------------
    # Step 2: Call start endpoint via ASGITransport (no live server needed)
    # -----------------------------------------------------------------------
    _section("STEP 2: Calling POST /session/{session_id}/start via ASGITransport")

    # Patch LiveKit calls — no live LiveKit server required
    mock_token = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        f".{base64.urlsafe_b64encode(json.dumps({'room': room_name, 'sub': MOCK_USER_ID, 'video': {'roomJoin': True}}).encode()).rstrip(b'=').decode()}"
        ".fakesignature"
    )

    try:
        async with LifespanManager(app) as manager:
            async with AsyncClient(
                transport=ASGITransport(app=manager.app),
                base_url="http://test",
            ) as client:

                with patch("api.routers.practice.provision_room", new_callable=AsyncMock) as mock_provision, \
                     patch("api.routers.practice.generate_token", new_callable=AsyncMock, return_value=mock_token):

                    # --- 2a. First call — expect 201 ---
                    resp = await client.post(f"/api/v1/practice/session/{session_id}/start")

                    if resp.status_code != 201:
                        _fail(
                            f"POST /session/{session_id}/start returned "
                            f"{resp.status_code}, expected 201\nBody: {resp.text}"
                        )
                    _pass(f"POST /session/{session_id}/start returned 201")

                    body = resp.json()

                    # Assert response shape
                    for field in ("livekit_token", "livekit_url", "room_name", "status"):
                        if field not in body:
                            _fail(f"Response missing field: '{field}'")
                    _pass(f"Response contains all required fields: livekit_token, livekit_url, room_name, status")

                    # Assert room_name value
                    if body["room_name"] != room_name:
                        _fail(f"room_name mismatch: expected '{room_name}', got '{body['room_name']}'")
                    _pass(f"room_name='{body['room_name']}' matches expected value")

                    # Assert status value
                    if body["status"] != "interviewing":
                        _fail(f"status mismatch: expected 'interviewing', got '{body['status']}'")
                    _pass(f"status='{body['status']}' is correct")

                    # Assert provision_room was called
                    mock_provision.assert_called_once()
                    _pass("provision_room was called once")

                    # --- 2b. Decode JWT and assert claims ---
                    _section("STEP 2b: Decoding JWT and asserting claims")

                    token = body["livekit_token"]
                    payload = _decode_jwt_payload(token)

                    if payload.get("room") != room_name:
                        _fail(
                            f"JWT 'room' claim mismatch: expected '{room_name}', "
                            f"got '{payload.get('room')}'"
                        )
                    _pass(f"JWT 'room' claim='{payload['room']}' matches room_name")

                    if payload.get("sub") != MOCK_USER_ID:
                        _fail(
                            f"JWT 'sub' claim mismatch: expected '{MOCK_USER_ID}', "
                            f"got '{payload.get('sub')}'"
                        )
                    _pass(f"JWT 'sub' claim='{payload['sub']}' matches user_id")

                    # --- 2c. Second call — expect 400 (idempotency guard) ---
                    _section("STEP 2c: Calling start endpoint again — expect 400")

                    resp2 = await client.post(f"/api/v1/practice/session/{session_id}/start")

                    if resp2.status_code != 400:
                        _fail(
                            f"Second call returned {resp2.status_code}, expected 400\n"
                            f"Body: {resp2.text}"
                        )
                    _pass(f"Second call correctly returned 400 (idempotency guard)")

                    detail = resp2.json().get("detail", "")
                    if "already been started" not in detail:
                        _fail(f"Unexpected 400 detail: '{detail}'")
                    _pass(f"400 detail message is correct: '{detail}'")

    except SystemExit:
        raise
    except Exception as exc:
        _fail(f"Unexpected error during endpoint calls: {exc}")

    # -----------------------------------------------------------------------
    # Step 3: Assert DB state
    # -----------------------------------------------------------------------
    _section("STEP 3: Asserting final database state")

    row = await conn.fetchrow(
        "SELECT status, livekit_room_name FROM practice_sessions WHERE id = $1",
        session_id,
    )

    if row is None:
        _fail(f"practice_sessions row not found for session_id={session_id}")

    if row["status"] != "interviewing":
        _fail(f"Expected status='interviewing', got '{row['status']}'")
    _pass(f"DB status='{row['status']}' is correct")

    if row["livekit_room_name"] != room_name:
        _fail(
            f"Expected livekit_room_name='{room_name}', "
            f"got '{row['livekit_room_name']}'"
        )
    _pass(f"DB livekit_room_name='{row['livekit_room_name']}' is correct")

    # -----------------------------------------------------------------------
    # Step 4: Cleanup
    # -----------------------------------------------------------------------
    _section("STEP 4: Cleaning up seeded rows")

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
    print("Phase 6 verification PASSED.")
    print(f"  session_id : {session_id}")
    print(f"  job_id     : {job_id}")
    print(f"  room_name  : {room_name}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
