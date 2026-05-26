# Requirements Document

## Introduction

Phase 5 builds the read layer of the Candidate Practice Portal backend. It exposes two FastAPI endpoints that allow the candidate's dashboard UI to list all historical practice sessions and poll the live processing status of any individual session. Once the async pipeline (Phase 4) transitions a session to `ready_to_start`, these endpoints also surface the full resume alignment report (score, strengths, weaknesses) so the frontend can render the pre-interview scorecard and unlock the "Start Interview" button.

All endpoints reuse the existing `asyncpg` connection pool, Pydantic v2 response models, and the mock `current_user_id` dependency pattern established in Phases 3 and 4.

---

## Glossary

- **Practice Portal**: The candidate-facing FastAPI application built across Phases 1–10.
- **Session**: A row in `practice_sessions` representing one end-to-end practice attempt by a candidate.
- **Job**: A row in `practice_jobs` storing the target job title and raw Job Description text uploaded by the candidate.
- **Pipeline Status**: The `status` column on `practice_sessions`. Valid values: `parsing`, `scoring`, `ready_to_start`, `interviewing`, `completed`.
- **Resume Report**: The JSONB payload stored in `practice_sessions.resume_report`, validated against `ResumeReportData` (score 0–100, reference summary, strengths list, weaknesses list).
- **Mock User ID**: The fixed UUID `a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d` used as the authenticated user identity until a real auth layer is introduced.
- **APIRouter**: FastAPI's modular router class used to group related path operations under a shared prefix.
- **asyncpg**: The asynchronous PostgreSQL driver used for all database interactions in this project.
- **Pydantic v2**: The data validation library used for all request and response models.
- **Dashboard**: The candidate-facing frontend view that lists all sessions and their current states.

---

## Requirements

### Requirement 1

**User Story:** As a candidate, I want to see a list of all my practice sessions on the dashboard, so that I can track my history and quickly identify which sessions are ready to start.

#### Acceptance Criteria

1. WHEN the candidate sends a `GET` request to `/api/v1/practice/sessions`, THE Practice Portal SHALL return an array of session summary objects ordered by `created_at` descending.
2. WHEN the candidate has no sessions, THE Practice Portal SHALL return an empty JSON array with a `200 OK` status.
3. THE Practice Portal SHALL include the following fields in each session summary: `session_id`, `status`, `created_at`, a nested `job` object containing `id` and `title`, and `resume_score`.
4. WHEN a session's `resume_report` JSONB column is NULL (pipeline still running), THE Practice Portal SHALL return `null` for the `resume_score` field rather than raising an error.
5. THE Practice Portal SHALL scope the query strictly to sessions belonging to the active `user_id`, returning no rows from other users.

---

### Requirement 2

**User Story:** As a candidate, I want to poll the status of a specific practice session, so that my dashboard can automatically update when the resume analysis is complete.

#### Acceptance Criteria

1. WHEN the candidate sends a `GET` request to `/api/v1/practice/session/{session_id}`, THE Practice Portal SHALL return the current `status` field of that session.
2. WHEN the requested `session_id` does not exist in the database, THE Practice Portal SHALL return a `404 Not Found` response with a descriptive error message.
3. WHEN the requested `session_id` belongs to a different user than the active `user_id`, THE Practice Portal SHALL return a `404 Not Found` response.
4. WHILE the session `status` is `parsing` or `scoring`, THE Practice Portal SHALL return the status field and `null` values for `resume_report` and `generated_questions`.
5. WHEN the session `status` is `ready_to_start`, `interviewing`, or `completed`, THE Practice Portal SHALL include the full `resume_report` payload (score, reference_to_jd, strengths, weaknesses) in the response.

---

### Requirement 3

**User Story:** As a developer, I want the new endpoints to use consistent response models and the existing dependency injection pattern, so that the codebase remains uniform and maintainable.

#### Acceptance Criteria

1. THE Practice Portal SHALL define all response shapes as Pydantic v2 `BaseModel` classes with explicit field types.
2. THE Practice Portal SHALL resolve the database connection for both new endpoints via the existing `get_db` dependency from `api/dependencies.py`.
3. THE Practice Portal SHALL extract the active `user_id` from a FastAPI `Depends` function that defaults to the Mock User ID `a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d`.
4. THE Practice Portal SHALL register both new endpoints on the existing `APIRouter` instance in `api/routers/practice.py` without creating a new router file.
5. WHEN a database query fails due to an `asyncpg` error, THE Practice Portal SHALL return a `500 Internal Server Error` response and log the exception with the relevant `session_id` or `user_id`.
