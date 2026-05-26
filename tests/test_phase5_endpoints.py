"""Unit tests for Phase 5 GET /sessions and GET /session/{id} endpoints.

Uses pytest-asyncio and unittest.mock.AsyncMock to mock the asyncpg connection,
so no live database is required.

Requirements: 1.2, 1.4, 2.2, 2.3, 2.4, 3.5
"""
import json
from datetime import datetime, timezone
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
NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

MOCK_RESUME_REPORT = {
    "score": 82,
    "reference_to_jd": "Strong alignment.",
    "strengths": ["Python", "FastAPI"],
    "weaknesses": ["No CI/CD"],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session_row(
    session_id=None,
    status="ready_to_start",
    resume_report=None,
    generated_questions=None,
    job_id=None,
    job_title="Test Job",
):
    """Build a dict that mimics an asyncpg Record for a session JOIN row."""
    row = MagicMock()
    row.__getitem__ = lambda self, key: {
        "session_id": session_id or uuid4(),
        "status": status,
        "created_at": NOW,
        "resume_report": resume_report,
        "generated_questions": generated_questions,
        "job_id": job_id or uuid4(),
        "job_title": job_title,
    }[key]
    return row


def _make_conn_mock(fetch_return=None, fetchrow_return=None, error=None):
    """Return a minimal asyncpg Connection mock."""
    conn = AsyncMock(spec=asyncpg.Connection)
    if error:
        conn.fetch = AsyncMock(side_effect=error)
        conn.fetchrow = AsyncMock(side_effect=error)
    else:
        conn.fetch = AsyncMock(return_value=fetch_return if fetch_return is not None else [])
        conn.fetchrow = AsyncMock(return_value=fetchrow_return)
    return conn


def _make_pool_mock(conn):
    """Wrap a connection mock in a minimal pool mock."""
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
# GET /api/v1/practice/sessions
# ---------------------------------------------------------------------------

async def test_list_sessions_empty(monkeypatch):
    """Requirement 1.2: empty session list returns 200 with []."""
    conn = _make_conn_mock(fetch_return=[])
    pool = _make_pool_mock(conn)

    app.state.db_pool = pool
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/practice/sessions")

    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_sessions_mixed_statuses(monkeypatch):
    """Requirement 1.4: sessions with and without resume_report return correct resume_score."""
    session_a_id = uuid4()
    session_b_id = uuid4()

    rows = [
        _make_session_row(session_id=session_a_id, status="ready_to_start", resume_report=MOCK_RESUME_REPORT),
        _make_session_row(session_id=session_b_id, status="parsing", resume_report=None),
    ]
    conn = _make_conn_mock(fetch_return=rows)
    pool = _make_pool_mock(conn)

    app.state.db_pool = pool
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/practice/sessions")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2

    ready = next(s for s in body if s["session_id"] == str(session_a_id))
    parsing = next(s for s in body if s["session_id"] == str(session_b_id))

    assert ready["resume_score"] == MOCK_RESUME_REPORT["score"]
    assert parsing["resume_score"] is None


async def test_list_sessions_db_error_returns_500():
    """Requirement 3.5: asyncpg error on list query returns 500."""
    conn = _make_conn_mock(error=asyncpg.PostgresError("connection lost"))
    pool = _make_pool_mock(conn)

    app.state.db_pool = pool
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/practice/sessions")

    assert resp.status_code == 500
    assert "Database error" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# GET /api/v1/practice/session/{session_id}
# ---------------------------------------------------------------------------

async def test_get_session_found_ready_to_start():
    """Requirement 2.2, 2.5: found session with ready_to_start exposes resume_report."""
    session_id = uuid4()
    row = _make_session_row(
        session_id=session_id,
        status="ready_to_start",
        resume_report=MOCK_RESUME_REPORT,
        generated_questions=[{"id": 1, "question": "Tell me about yourself."}],
    )
    conn = _make_conn_mock(fetchrow_return=row)
    pool = _make_pool_mock(conn)

    app.state.db_pool = pool
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/practice/session/{session_id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready_to_start"
    assert body["resume_report"]["score"] == MOCK_RESUME_REPORT["score"]
    assert body["generated_questions"] is not None


async def test_get_session_parsing_hides_report():
    """Requirement 2.4: session in parsing status returns null for resume_report and generated_questions."""
    session_id = uuid4()
    row = _make_session_row(
        session_id=session_id,
        status="parsing",
        resume_report=None,
        generated_questions=None,
    )
    conn = _make_conn_mock(fetchrow_return=row)
    pool = _make_pool_mock(conn)

    app.state.db_pool = pool
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/practice/session/{session_id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["resume_report"] is None
    assert body["generated_questions"] is None


async def test_get_session_not_found_returns_404():
    """Requirement 2.2: missing session_id returns 404."""
    conn = _make_conn_mock(fetchrow_return=None)
    pool = _make_pool_mock(conn)

    app.state.db_pool = pool
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/practice/session/{uuid4()}")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Session not found."


async def test_get_session_wrong_user_returns_404():
    """Requirement 2.3: session belonging to another user returns 404 (fetchrow returns None)."""
    # The SQL filters by both session_id AND user_id, so a wrong-user row simply
    # returns no result — same as not found.
    conn = _make_conn_mock(fetchrow_return=None)
    pool = _make_pool_mock(conn)

    app.state.db_pool = pool
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/practice/session/{uuid4()}")

    assert resp.status_code == 404


async def test_get_session_db_error_returns_500():
    """Requirement 3.5: asyncpg error on detail query returns 500."""
    conn = _make_conn_mock(error=asyncpg.PostgresError("timeout"))
    pool = _make_pool_mock(conn)

    app.state.db_pool = pool
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/practice/session/{uuid4()}")

    assert resp.status_code == 500
    assert "Database error" in resp.json()["detail"]
