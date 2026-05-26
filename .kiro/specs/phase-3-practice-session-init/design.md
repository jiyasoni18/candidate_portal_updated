# Design Document: Phase 3 — Practice Session Initialization & Local File Upload Router

## Overview

Phase 3 introduces the first live HTTP endpoint of the Candidate Portal: `POST /api/v1/practice/initialize`. Its sole responsibility is to accept a multipart form upload, persist the PDF to local disk, write two coordinated PostgreSQL rows, schedule the Phase 4 background pipeline, and return a `201 Created` response — all within a single non-blocking async handler. No LLM calls, no file parsing, and no scoring happen in this phase. The endpoint is intentionally thin: it initializes state and immediately yields control.

---

## Architecture

```mermaid
graph TD
    A[Client: multipart/form-data POST] --> B[FastAPI: POST /api/v1/practice/initialize]
    B --> C{Validate form fields}
    C -->|422| D[Return Unprocessable Entity]
    C -->|valid| E[Generate session_id + job_id UUIDs]
    E --> F[Write PDF to ./storage/resumes/session_id/resume.pdf]
    F -->|filesystem error| G[Return 500 - no DB writes]
    F -->|success| H[Open asyncpg connection]
    H --> I[INSERT practice_jobs row]
    I --> J[INSERT practice_sessions row with status=parsing]
    J -->|DB error| K[Rollback + Return 500]
    J -->|commit| L[Schedule BackgroundTasks callback]
    L --> M[Return 201 InitializeSessionResponse]
    L -.->|async, non-blocking| N[Phase 4 Processing Pipeline]
```

The handler is strictly sequential up to the `BackgroundTasks` registration. The background task fires after the response is sent — FastAPI guarantees this ordering with its native `BackgroundTasks` mechanism.

---

## Components and Interfaces

### Directory Structure

```
main.py                          # FastAPI app factory + router registration
api/
├── __init__.py
├── dependencies.py              # DB connection pool dependency
└── routers/
    ├── __init__.py
    └── practice.py              # POST /api/v1/practice/initialize
schemas/
└── (Phase 2 — already exists)
storage/
└── resumes/                     # Created at runtime; gitignored
```

### `main.py` — Application Entry Point

Creates the `FastAPI` instance, registers CORS middleware, and mounts the practice router under `/api/v1`.

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers.practice import router as practice_router

app = FastAPI(title="Candidate Practice Portal")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(practice_router, prefix="/api/v1")
```

### `api/dependencies.py` — DB Connection Dependency

Provides a FastAPI dependency that yields an `asyncpg` connection from a module-level connection pool. The pool is initialized on application startup via a lifespan event.

```python
import asyncpg
from fastapi import Request

async def get_db(request: Request) -> asyncpg.Connection:
    async with request.app.state.db_pool.acquire() as conn:
        yield conn
```

The pool is created in `main.py`'s lifespan context:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db_pool = await asyncpg.create_pool(dsn=settings.DATABASE_URL)
    yield
    await app.state.db_pool.close()
```

### `api/routers/practice.py` — Initialization Router

The core of this phase. Key design decisions:

- **File I/O before DB writes**: If the filesystem write fails, no DB rows are created. This avoids orphaned session records pointing to non-existent files.
- **Single transaction for both INSERTs**: `practice_jobs` and `practice_sessions` are inserted within one `asyncpg` transaction block. Either both succeed or neither does.
- **`aiofiles` for async file writes**: Avoids blocking the event loop during PDF write. The `aiofiles` library is the standard choice for async file I/O in FastAPI applications.
- **`BackgroundTasks` registration after commit**: The background task is only scheduled after the transaction commits successfully, preventing phantom task executions for failed sessions.

### `InitializeSessionResponse` — Response Model

Defined in `api/routers/practice.py` (or a dedicated `api/schemas.py` if the project grows):

```python
from pydantic import BaseModel
from uuid import UUID

class InitializeSessionResponse(BaseModel):
    session_id: UUID
    job_id: UUID
    status: str
    message: str

    model_config = {"json_encoders": {UUID: str}}
```

---

## Data Models

### Form Input

| Field | Type | Required | Default |
|---|---|---|---|
| `file` | `UploadFile` | Yes | — |
| `jd_text` | `str` | Yes | — |
| `user_id` | `UUID` | No | `a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d` |

FastAPI's `Form(...)` and `File(...)` annotations handle multipart parsing and `422` generation automatically for missing required fields.

### `practice_jobs` INSERT

| Column | Value |
|---|---|
| `id` | Generated `job_id` UUID |
| `user_id` | From form field |
| `title` | `"Target Job Role"` (hardcoded fallback) |
| `description` | `jd_text` from form |
| `jd_parsed` | NULL |

### `practice_sessions` INSERT

| Column | Value |
|---|---|
| `id` | Generated `session_id` UUID |
| `user_id` | From form field |
| `job_id` | `job_id` from preceding insert |
| `resume_url` | `./storage/resumes/{session_id}/resume.pdf` |
| `status` | `'parsing'` |
| All JSONB columns | NULL |

### `InitializeSessionResponse` JSON Body

```json
{
  "session_id": "d3c2b1a0-9f8e-7d6c-5b4a-3f2e1d0c9b8a",
  "job_id": "e4b11f20-80a8-48b6-b51f-6fa12a43312c",
  "status": "parsing",
  "message": "Practice session initialized. Async processing pipelines triggered successfully."
}
```

---

## Error Handling

| Scenario | HTTP Status | DB State | File State |
|---|---|---|---|
| Missing `file` field | `422 Unprocessable Entity` | No writes | No writes |
| Missing/empty `jd_text` | `422 Unprocessable Entity` | No writes | No writes |
| `os.makedirs` or `aiofiles.open` fails | `500 Internal Server Error` | No writes | Partial/none |
| `practice_jobs` INSERT fails | `500 Internal Server Error` | Rolled back | File written |
| `practice_sessions` INSERT fails | `500 Internal Server Error` | Rolled back | File written |
| Both INSERTs succeed | `201 Created` | Committed | File written |

Note: if the DB transaction fails after a successful file write, the orphaned file at `./storage/resumes/{session_id}/resume.pdf` is left on disk. A cleanup task is out of scope for this phase; the storage directory is local and ephemeral in the Docker environment.

All unhandled exceptions are caught by a top-level `try/except` block in the handler that returns a structured `500` response with a generic error message, preventing raw tracebacks from leaking to the client.

---

## Configuration

A `config.py` module (or `.env`-backed `pydantic-settings` model) will hold the database DSN and storage root path:

```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://practice_user:practice_password_2026@localhost:5432/interview_practice_db"
    STORAGE_ROOT: str = "./storage/resumes"

    class Config:
        env_file = ".env"

settings = Settings()
```

The `DATABASE_URL` default matches the `docker-compose.yml` service credentials from Phase 1. The `STORAGE_ROOT` is used by the router to construct file paths, making it overridable via environment variable without code changes.

---

## Testing Strategy

The primary verification method specified in `phase3.md` is a `curl` command against the running Docker stack:

```bash
curl -X POST "http://localhost:8000/api/v1/practice/initialize" \
  -F "file=@sample_resume.pdf" \
  -F "jd_text=Seeking a Software Engineer experienced in Python and FastAPI..."
```

Expected outcomes to verify:
1. HTTP `201` response with the correct JSON body shape.
2. File exists at `./storage/resumes/{session_id}/resume.pdf` inside the container.
3. A row exists in `practice_jobs` with the matching `job_id`.
4. A row exists in `practice_sessions` with `status = 'parsing'` and the correct `resume_url`.

A lightweight Python verification script (`scripts/verify_phase3.py`) can be included to automate the `curl` check and DB query using `asyncpg` directly, matching the pattern from Phase 1's `database/verify.sql`.

Unit tests for the router are marked optional in the task list. If written, they should use `httpx.AsyncClient` with FastAPI's `TestClient` or `ASGITransport`, mocking the `asyncpg` pool and `aiofiles` calls to avoid requiring a live database.
