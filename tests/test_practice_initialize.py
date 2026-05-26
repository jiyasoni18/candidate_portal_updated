"""Integration tests for POST /api/v1/practice/initialize.

Requires a running PostgreSQL instance matching the DATABASE_URL in config.py
(i.e. the docker-compose stack from Phase 1 must be up).
"""
import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from config import settings
from main import app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def lifespan_app(tmp_path, monkeypatch):
    """Start the app with its full lifespan (creates db_pool) and patch storage root."""
    import api.routers.practice as practice_module

    monkeypatch.setattr(settings, "STORAGE_ROOT", str(tmp_path))
    monkeypatch.setattr(practice_module.settings, "STORAGE_ROOT", str(tmp_path))

    async with LifespanManager(app) as manager:
        yield manager.app


@pytest_asyncio.fixture
async def client(lifespan_app):
    """AsyncClient wired to the fully-initialized ASGI app."""
    async with AsyncClient(
        transport=ASGITransport(app=lifespan_app), base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def db_conn(lifespan_app):
    """Reuse the app's asyncpg pool for assertion queries."""
    async with app.state.db_pool.acquire() as conn:
        yield conn


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pdf_bytes() -> bytes:
    return b"%PDF-1.4 test resume content"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_initialize_returns_201_with_correct_shape(client):
    """Requirement 1.3, 5.1, 5.2: successful request returns 201 with expected JSON fields."""
    response = await client.post(
        "/api/v1/practice/initialize",
        files={"file": ("resume.pdf", _pdf_bytes(), "application/pdf")},
        data={"jd_text": "Seeking a Python/FastAPI engineer."},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "parsing"
    assert (
        body["message"]
        == "Practice session initialized. Async processing pipelines triggered successfully."
    )
    assert "session_id" in body
    assert "job_id" in body


async def test_initialize_writes_file_to_disk(client, lifespan_app, tmp_path):
    """Requirement 2.2: uploaded file is persisted at the expected path."""
    response = await client.post(
        "/api/v1/practice/initialize",
        files={"file": ("resume.pdf", _pdf_bytes(), "application/pdf")},
        data={"jd_text": "Looking for a backend engineer."},
    )
    assert response.status_code == 201
    session_id = response.json()["session_id"]
    expected_path = tmp_path / session_id / "resume.pdf"
    assert expected_path.exists(), f"Expected file at {expected_path}"


async def test_initialize_inserts_db_rows(client, db_conn):
    """Requirements 3.1, 3.2: practice_jobs and practice_sessions rows are created."""
    response = await client.post(
        "/api/v1/practice/initialize",
        files={"file": ("resume.pdf", _pdf_bytes(), "application/pdf")},
        data={"jd_text": "Senior Python developer role."},
    )
    assert response.status_code == 201
    body = response.json()
    session_id = body["session_id"]
    job_id = body["job_id"]

    job_row = await db_conn.fetchrow("SELECT * FROM practice_jobs WHERE id = $1", job_id)
    assert job_row is not None
    assert job_row["description"] == "Senior Python developer role."

    session_row = await db_conn.fetchrow(
        "SELECT * FROM practice_sessions WHERE id = $1", session_id
    )
    assert session_row is not None
    assert session_row["status"] == "parsing"
    assert str(session_row["job_id"]) == job_id

    # Cleanup
    await db_conn.execute("DELETE FROM practice_sessions WHERE id = $1", session_id)
    await db_conn.execute("DELETE FROM practice_jobs WHERE id = $1", job_id)


async def test_initialize_422_on_missing_file(client):
    """Requirement 1.4: missing file field returns 422."""
    response = await client.post(
        "/api/v1/practice/initialize",
        data={"jd_text": "Some job description."},
    )
    assert response.status_code == 422


async def test_initialize_422_on_missing_jd_text(client):
    """Requirement 1.5: missing jd_text field returns 422."""
    response = await client.post(
        "/api/v1/practice/initialize",
        files={"file": ("resume.pdf", _pdf_bytes(), "application/pdf")},
    )
    assert response.status_code == 422
