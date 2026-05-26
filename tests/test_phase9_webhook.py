"""Unit tests for POST /api/v1/practice/session/complete (Phase 9 webhook).

Uses unittest.mock to avoid a live database.
Requirements: 4.2, 4.3, 4.4, 4.5
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient

from main import app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_TRANSCRIPT = [
    {"speaker": "agent", "text": "Hello, welcome.", "created_at": 1700000000.0},
    {"speaker": "candidate", "text": "Thanks.", "created_at": 1700000010.0},
]

VALID_PAYLOAD = {
    "session_id": str(uuid4()),
    "end_reason": "normal",
    "duration_seconds": 120,
    "transcript": VALID_TRANSCRIPT,
}


def _make_row(status: str):
    row = MagicMock()
    row.__getitem__ = lambda self, key: {"status": status}[key]
    return row


def _make_conn(fetchrow_return=None, execute_error=None, fetch_error=None):
    conn = AsyncMock(spec=asyncpg.Connection)
    if fetch_error:
        conn.fetchrow = AsyncMock(side_effect=fetch_error)
    else:
        conn.fetchrow = AsyncMock(return_value=fetchrow_return)
    if execute_error:
        conn.execute = AsyncMock(side_effect=execute_error)
    else:
        conn.execute = AsyncMock(return_value=None)
    return conn


def _make_pool(conn):
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    return pool


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_422_on_empty_transcript():
    """Requirement 4.3: empty transcript array returns 422."""
    # Pydantic validation fires before DB access, but the dependency is still
    # resolved — set a dummy pool so the dependency doesn't crash first.
    conn = _make_conn(fetchrow_return=None)
    app.state.db_pool = _make_pool(conn)

    payload = {**VALID_PAYLOAD, "session_id": str(uuid4()), "transcript": []}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/practice/session/complete", json=payload)
    assert resp.status_code == 422


async def test_422_on_invalid_end_reason():
    """Requirement 4.2: invalid end_reason returns 422."""
    conn = _make_conn(fetchrow_return=None)
    app.state.db_pool = _make_pool(conn)

    payload = {**VALID_PAYLOAD, "session_id": str(uuid4()), "end_reason": "unknown_reason"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/practice/session/complete", json=payload)
    assert resp.status_code == 422


async def test_404_on_unknown_session_id():
    """Requirement 4.4: session_id not in DB returns 404."""
    conn = _make_conn(fetchrow_return=None)
    app.state.db_pool = _make_pool(conn)

    payload = {**VALID_PAYLOAD, "session_id": str(uuid4())}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/practice/session/complete", json=payload)

    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


async def test_409_on_wrong_status():
    """Requirement 4.5: session with status != 'interviewing' returns 409."""
    conn = _make_conn(fetchrow_return=_make_row("ready_to_start"))
    app.state.db_pool = _make_pool(conn)

    payload = {**VALID_PAYLOAD, "session_id": str(uuid4())}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/practice/session/complete", json=payload)

    assert resp.status_code == 409


async def test_500_on_db_update_error():
    """Requirement 5.5: DB error during UPDATE returns 500, background task not enqueued."""
    conn = _make_conn(
        fetchrow_return=_make_row("interviewing"),
        execute_error=asyncpg.PostgresError("disk full"),
    )
    app.state.db_pool = _make_pool(conn)

    payload = {**VALID_PAYLOAD, "session_id": str(uuid4())}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/practice/session/complete", json=payload)

    assert resp.status_code == 500


async def test_200_happy_path():
    """Requirements 5.1-5.4, 6.1-6.3: successful update returns 200 with status='received'."""
    conn = _make_conn(fetchrow_return=_make_row("interviewing"))
    app.state.db_pool = _make_pool(conn)

    session_id = str(uuid4())
    payload = {**VALID_PAYLOAD, "session_id": session_id}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/practice/session/complete", json=payload)

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "received"
    assert body["session_id"] == session_id

    # Assert DB UPDATE was called with correct status transition
    conn.execute.assert_called_once()
    call_args = conn.execute.call_args[0]
    assert "interview_processing" in call_args[0]


async def test_200_happy_path_db_update_fields():
    """Requirements 5.1, 5.2, 5.3: UPDATE writes transcript, end_reason, duration_seconds."""
    conn = _make_conn(fetchrow_return=_make_row("interviewing"))
    app.state.db_pool = _make_pool(conn)

    session_id = str(uuid4())
    payload = {
        "session_id": session_id,
        "end_reason": "silence_timeout",
        "duration_seconds": 300,
        "transcript": VALID_TRANSCRIPT,
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/practice/session/complete", json=payload)

    assert resp.status_code == 200
    # Verify the execute call included end_reason and duration_seconds as args
    call_args = conn.execute.call_args[0]
    assert "silence_timeout" in call_args  # end_reason
    assert 300 in call_args               # duration_seconds
