"""Unit tests for POST /api/v1/auth/register and /api/v1/auth/login.

Uses AsyncMock to mock the asyncpg connection — no live database required.

Requirements: 3.1, 3.2, 3.3, 3.4
"""
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient

from main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_conn_mock(fetchrow_return=None, execute_side_effect=None):
    conn = AsyncMock(spec=asyncpg.Connection)
    conn.fetchrow = AsyncMock(return_value=fetchrow_return)
    if execute_side_effect:
        conn.execute = AsyncMock(side_effect=execute_side_effect)
    return conn


def _make_pool_mock(conn):
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    return pool


# ---------------------------------------------------------------------------
# POST /api/v1/auth/register
# ---------------------------------------------------------------------------

async def test_register_success():
    """Requirement 3.3: successful registration returns 200 with access_token."""
    new_id = uuid4()
    row = MagicMock()
    row.__getitem__ = lambda self, key: new_id if key == "id" else None

    conn = AsyncMock(spec=asyncpg.Connection)
    conn.fetchrow = AsyncMock(return_value=row)
    pool = _make_pool_mock(conn)

    app.state.db_pool = pool
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/register",
            json={"full_name": "Alice Smith", "email": "alice@example.com", "password": "securepass"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


async def test_register_duplicate_email_returns_409():
    """Requirement 3.4: duplicate email returns HTTP 409."""
    conn = AsyncMock(spec=asyncpg.Connection)
    conn.fetchrow = AsyncMock(side_effect=asyncpg.UniqueViolationError("duplicate key"))
    pool = _make_pool_mock(conn)

    app.state.db_pool = pool
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/register",
            json={"full_name": "Bob", "email": "bob@example.com", "password": "securepass"},
        )

    assert resp.status_code == 409
    assert "already registered" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# POST /api/v1/auth/login
# ---------------------------------------------------------------------------

async def test_login_success():
    """Requirement 3.1: valid credentials return 200 with access_token."""
    import bcrypt
    hashed = bcrypt.hashpw(b"mypassword", bcrypt.gensalt()).decode()
    user_id = uuid4()

    row = MagicMock()
    row.__getitem__ = lambda self, key: {
        "id": user_id,
        "hashed_password": hashed,
    }[key]

    conn = AsyncMock(spec=asyncpg.Connection)
    conn.fetchrow = AsyncMock(return_value=row)
    pool = _make_pool_mock(conn)

    app.state.db_pool = pool
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "alice@example.com", "password": "mypassword"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


async def test_login_wrong_password_returns_401():
    """Requirement 3.2: wrong password returns HTTP 401."""
    import bcrypt
    hashed = bcrypt.hashpw(b"correctpassword", bcrypt.gensalt()).decode()
    user_id = uuid4()

    row = MagicMock()
    row.__getitem__ = lambda self, key: {
        "id": user_id,
        "hashed_password": hashed,
    }[key]

    conn = AsyncMock(spec=asyncpg.Connection)
    conn.fetchrow = AsyncMock(return_value=row)
    pool = _make_pool_mock(conn)

    app.state.db_pool = pool
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "alice@example.com", "password": "wrongpassword"},
        )

    assert resp.status_code == 401
    assert "Invalid email or password" in resp.json()["detail"]


async def test_login_unknown_email_returns_401():
    """Requirement 3.2: unknown email returns HTTP 401."""
    conn = AsyncMock(spec=asyncpg.Connection)
    conn.fetchrow = AsyncMock(return_value=None)
    pool = _make_pool_mock(conn)

    app.state.db_pool = pool
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "anypassword"},
        )

    assert resp.status_code == 401
    assert "Invalid email or password" in resp.json()["detail"]
