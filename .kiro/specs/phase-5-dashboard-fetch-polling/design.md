# Design Document: Phase 5 — Dashboard Session Fetch & Polling Endpoints

## Overview

Phase 5 adds two read-only `GET` endpoints to the existing `api/routers/practice.py` router. These endpoints give the candidate's dashboard UI the data it needs to render the session list and poll individual session state until the Phase 4 async pipeline finishes.

No new files are created. All additions are made inside the existing router module, reusing the established `get_db` dependency, the `asyncpg` pool, and the Pydantic v2 schema patterns from Phases 2–4.

---

## Architecture

```mermaid
graph TD
    A[Dashboard UI] -->|GET /api/v1/practice/sessions| B[list_sessions endpoint]
    A -->|GET /api/v1/practice/session/{id}| C[get_session endpoint]

    B --> D[get_current_user_id dependency\ndefaults to Mock User ID]
    C --> D

    B --> E[get_db dependency\nasyncpg Connection]
    C --> E

    B --> F[SQL: JOIN practice_sessions + practice_jobs\nWHERE user_id = $1\nORDER BY created_at DESC]
    C --> G[SQL: SELECT practice_sessions\nWHERE id = $1 AND user_id = $2]

    F --> H[SessionSummary list response]
    G -->|row found| I[SessionDetailResponse]
    G -->|row not found| J[404 HTTPException]
```

### Status-Conditional Response Logic

```
session.status == 'parsing' or 'scoring'
  → resume_report = null
  → generated_questions = null

session.status == 'ready_to_start' or 'interviewing' or 'completed'
  → resume_report = full ResumeReportData payload
  → generated_questions = QuestionArraySchema payload (detail endpoint only)
```

---

## Components and Interfaces

### Modified Files

```
api/routers/practice.py    # Add response models + two new GET endpoints
```

No new files are introduced. Both endpoints are appended to the existing router.

---

### New Pydantic Response Models (inside `api/routers/practice.py`)

#### `JobSummary`

Nested object embedded in `SessionSummary`.

```python
class JobSummary(BaseModel):
    id: UUID
    title: str

    @field_serializer("id")
    def serialize_uuid(self, v: UUID) -> str:
        return str(v)
```

#### `SessionSummary`

Response item for the list endpoint. `resume_score` is `None` when the pipeline has not yet produced a report.

```python
class SessionSummary(BaseModel):
    session_id: UUID
    status: str
    created_at: datetime
    job: JobSummary
    resume_score: Optional[int] = None

    @field_serializer("session_id")
    def serialize_uuid(self, v: UUID) -> str:
        return str(v)
```

#### `SessionDetailResponse`

Response for the single-session polling endpoint. `resume_report` and `generated_questions` are `None` while the pipeline is still running.

```python
class SessionDetailResponse(BaseModel):
    session_id: UUID
    status: str
    created_at: datetime
    job: JobSummary
    resume_report: Optional[dict] = None
    generated_questions: Optional[list] = None

    @field_serializer("session_id")
    def serialize_uuid(self, v: UUID) -> str:
        return str(v)
```

Using `dict` / `list` for the JSONB fields keeps the response flexible and avoids re-validating already-validated pipeline output on every read. The frontend consumes these as raw JSON.

---

### `get_current_user_id` Dependency

A lightweight FastAPI dependency that returns the mock user UUID. Placed at module level in `api/routers/practice.py` so both endpoints share it.

```python
_DEFAULT_USER_ID = UUID("a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d")

async def get_current_user_id() -> UUID:
    return _DEFAULT_USER_ID
```

This mirrors the pattern already used in the `initialize_session` endpoint and is trivially replaceable with a real JWT-based dependency in a future phase.

---

### Endpoint 1: `GET /api/v1/practice/sessions`

**Handler:** `list_sessions`

**SQL Query:**

```sql
SELECT
    ps.id          AS session_id,
    ps.status,
    ps.created_at,
    ps.resume_report,
    pj.id          AS job_id,
    pj.title       AS job_title
FROM practice_sessions ps
INNER JOIN practice_jobs pj ON ps.job_id = pj.id
WHERE ps.user_id = $1
ORDER BY ps.created_at DESC;
```

**Response construction:**

- Iterate over rows.
- Extract `resume_score` from `row["resume_report"]["score"]` if `resume_report` is not `None`, otherwise `None`.
- Build a `SessionSummary` per row.
- Return the list directly (FastAPI serializes it via `response_model=list[SessionSummary]`).

**Error handling:**

- `asyncpg.PostgresError` → log with `user_id`, raise `HTTPException(500)`.

---

### Endpoint 2: `GET /api/v1/practice/session/{session_id}`

**Handler:** `get_session`

**SQL Query:**

```sql
SELECT
    ps.id          AS session_id,
    ps.status,
    ps.created_at,
    ps.resume_report,
    ps.generated_questions,
    pj.id          AS job_id,
    pj.title       AS job_title
FROM practice_sessions ps
INNER JOIN practice_jobs pj ON ps.job_id = pj.id
WHERE ps.id = $1 AND ps.user_id = $2;
```

**Response construction:**

- If no row returned → `HTTPException(404, detail="Session not found.")`.
- Determine `resume_report` and `generated_questions` visibility based on status:
  - Statuses `parsing`, `scoring` → both fields `None`.
  - Statuses `ready_to_start`, `interviewing`, `completed` → pass JSONB values through as-is.
- Return `SessionDetailResponse`.

**Error handling:**

- `asyncpg.PostgresError` → log with `session_id`, raise `HTTPException(500)`.

---

## Data Models

No new database columns or tables are introduced. Phase 5 is purely a read layer over the schema established in Phase 1.

| Column read | Table | Type | Notes |
|---|---|---|---|
| `id` | `practice_sessions` | UUID | Returned as `session_id` |
| `status` | `practice_sessions` | VARCHAR(50) | Drives conditional field exposure |
| `created_at` | `practice_sessions` | TIMESTAMPTZ | Returned as-is |
| `resume_report` | `practice_sessions` | JSONB | `null` until Pipeline 2 completes |
| `generated_questions` | `practice_sessions` | JSONB | `null` until Pipeline 2 completes; detail endpoint only |
| `id` | `practice_jobs` | UUID | Returned as `job.id` |
| `title` | `practice_jobs` | VARCHAR(255) | Returned as `job.title` |

---

## Error Handling

| Scenario | HTTP Status | Detail |
|---|---|---|
| `session_id` not found or belongs to another user | `404` | `"Session not found."` |
| `asyncpg.PostgresError` on list query | `500` | `"Database error fetching sessions."` |
| `asyncpg.PostgresError` on detail query | `500` | `"Database error fetching session."` |

All exceptions are logged with the relevant identifier (`user_id` or `session_id`) before raising.

---

## Testing Strategy

### Verification Script (`scripts/verify_phase5.py`)

A standalone async script (mirroring `verify_phase4.py`) that:

1. Connects directly to the `asyncpg` pool using `config.settings.DATABASE_URL`.
2. Seeds a test session row with `status='ready_to_start'` and a mock `resume_report` JSONB payload.
3. Calls the FastAPI app via `httpx.AsyncClient` with `ASGITransport` (no live server needed).
4. Asserts:
   - `GET /api/v1/practice/sessions` returns `200` with at least one item containing `resume_score`.
   - `GET /api/v1/practice/session/{seeded_id}` returns `200` with `resume_report` populated.
   - `GET /api/v1/practice/session/{random_uuid}` returns `404`.
5. Cleans up the seeded row after assertions.
