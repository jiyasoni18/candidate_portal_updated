"""Integration tests for Phase 6 POST /session/{session_id}/start endpoint.

Uses unittest.mock to mock asyncpg connection and LiveKit helper functions.
No live database or LiveKit server required.

Requirements: 1.2, 1.3, 1.4, 3.3
"""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient

from main import app

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MOCK_USER_ID = UUID("a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d")
MOCK_SESSION_ID = uuid4()

MOCK_QUESTIONS = [{"id": 1, "question": "Tell me about yourself.", "category": "opening", "expected_duration_seconds": 120}]
MOCK_RESUME_REPORT = {"score": 85, "strengths": ["Python"], "weaknesses": []}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session_row(status="ready_to_start", session_id=None, user_id=None):
    """Build a mock asyncpg Record for the start endpoint JOIN query."""
    row = MagicMock()
    row.__getitem__ = lambda self, key: {
        "session_id": session_id or MOCK_SESSION_ID,
        "user_id": user_id or MOCK_USER_ID,
        "status": status,
        "generated_questions": MOCK_QUESTIONS,
        "resume_report": MOCK_RESUME_REPORT,
        "job_title": "Software Engineer",
        "job_description": "Build great software.",
        "candidate_name": "Jane Doe",
    }[key]
    return row


def _make_conn_mock(fetchrow_return=None, fetchrow_error=None, execute_error=None):
    conn = AsyncMock(spec=asyncpg.Connection)
    if fetchrow_error:
        conn.fetchrow = AsyncMock(side_effect=fetchrow_error)
    else:
        conn.fetchrow = AsyncMock(return_value=fetchrow_return)
    if execute_error:
        conn.execute = AsyncMock(side_effect=execute_error)
    else:
        conn.execute = AsyncMock(return_value=None)
    return conn


def _make_pool_mock(conn):
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    return pool


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def anyio_backend():
    return "asyncio"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_start_session_404_unknown_session():
    """Requirement 1.2: unknown session_id returns 404."""
    conn = _make_conn_mock(fetchrow_return=None)
    app.state.db_pool = _make_pool_mock(conn)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(f"/api/v1/practice/session/{uuid4()}/start")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Session not found."


async def test_start_session_400_status_parsing():
    """Requirement 1.3: status=parsing returns 400 with processing message."""
    conn = _make_conn_mock(fetchrow_return=_make_session_row(status="parsing"))
    app.state.db_pool = _make_pool_mock(conn)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(f"/api/v1/practice/session/{MOCK_SESSION_ID}/start")

    assert resp.status_code == 400
    assert "still processing" in resp.json()["detail"]


async def test_start_session_400_status_scoring():
    """Requirement 1.3: status=scoring returns 400 with processing message."""
    conn = _make_conn_mock(fetchrow_return=_make_session_row(status="scoring"))
    app.state.db_pool = _make_pool_mock(conn)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(f"/api/v1/practice/session/{MOCK_SESSION_ID}/start")

    assert resp.status_code == 400
    assert "still processing" in resp.json()["detail"]


async def test_start_session_400_status_interviewing():
    """Requirement 1.4: status=interviewing returns 400 with already started message."""
    conn = _make_conn_mock(fetchrow_return=_make_session_row(status="interviewing"))
    app.state.db_pool = _make_pool_mock(conn)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(f"/api/v1/practice/session/{MOCK_SESSION_ID}/start")

    assert resp.status_code == 400
    assert "already been started" in resp.json()["detail"]


async def test_start_session_400_status_completed():
    """Requirement 1.4: status=completed returns 400 with already completed message."""
    conn = _make_conn_mock(fetchrow_return=_make_session_row(status="completed"))
    app.state.db_pool = _make_pool_mock(conn)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(f"/api/v1/practice/session/{MOCK_SESSION_ID}/start")

    assert resp.status_code == 400
    assert "already been completed" in resp.json()["detail"]


async def test_start_session_503_on_provision_room_failure():
    """Requirement 3.3: LiveKit room provisioning failure returns 503."""
    from api.livekit_helper import LiveKitProvisionError

    conn = _make_conn_mock(fetchrow_return=_make_session_row(status="ready_to_start"))
    app.state.db_pool = _make_pool_mock(conn)

    with patch("api.routers.practice.provision_room", side_effect=LiveKitProvisionError("server down")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(f"/api/v1/practice/session/{MOCK_SESSION_ID}/start")

    assert resp.status_code == 503
    assert "provisioning failed" in resp.json()["detail"]


async def test_start_session_503_on_generate_token_failure():
    """Requirement 3.3: LiveKit token generation failure returns 503."""
    from api.livekit_helper import LiveKitTokenError

    conn = _make_conn_mock(fetchrow_return=_make_session_row(status="ready_to_start"))
    app.state.db_pool = _make_pool_mock(conn)

    with patch("api.routers.practice.provision_room", return_value=None), \
         patch("api.routers.practice.generate_token", side_effect=LiveKitTokenError("signing failed")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(f"/api/v1/practice/session/{MOCK_SESSION_ID}/start")

    assert resp.status_code == 503
    assert "token generation failed" in resp.json()["detail"]


async def test_start_session_201_success():
    """Requirement 5.1: successful start returns 201 with all required fields."""
    conn = _make_conn_mock(fetchrow_return=_make_session_row(status="ready_to_start"))
    app.state.db_pool = _make_pool_mock(conn)

    with patch("api.routers.practice.provision_room", return_value=None), \
         patch("api.routers.practice.generate_token", return_value="mock.jwt.token"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(f"/api/v1/practice/session/{MOCK_SESSION_ID}/start")

    assert resp.status_code == 201
    body = resp.json()
    assert body["livekit_token"] == "mock.jwt.token"
    assert body["room_name"] == f"practice-room-{MOCK_SESSION_ID}"
    assert body["status"] == "interviewing"
    assert "livekit_url" in body
