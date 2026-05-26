# Implementation Plan

- [x] 1. Add response models for Phase 5 endpoints





  - Define `JobSummary`, `SessionSummary`, and `SessionDetailResponse` Pydantic v2 models inside `api/routers/practice.py`
  - Add `get_current_user_id` dependency function returning the mock UUID `a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d`
  - _Requirements: 3.1, 3.3_

- [x] 2. Implement `GET /api/v1/practice/sessions` list endpoint





  - Add `list_sessions` async handler to the existing router in `api/routers/practice.py`
  - Execute the JOIN query against `practice_sessions` and `practice_jobs` filtered by `user_id`, ordered by `created_at DESC`
  - Extract `resume_score` from `resume_report` JSONB when present, return `null` otherwise
  - Handle `asyncpg.PostgresError` with a `500` response and log the error
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 3.2, 3.4, 3.5_

- [x] 3. Implement `GET /api/v1/practice/session/{session_id}` detail endpoint





  - Add `get_session` async handler to the existing router in `api/routers/practice.py`
  - Execute the JOIN query filtered by both `session_id` and `user_id`
  - Return `404` when no row is found (covers missing ID and wrong-user cases)
  - Conditionally expose `resume_report` and `generated_questions` based on session status
  - Handle `asyncpg.PostgresError` with a `500` response and log the error
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.2, 3.4, 3.5_

- [x] 4. Write verification script





- [x] 4.1 Create `scripts/verify_phase5.py`


  - Seed a test session with `status='ready_to_start'` and a mock `resume_report` payload
  - Use `httpx.AsyncClient` with `ASGITransport` to call both endpoints without a live server
  - Assert list endpoint returns `200` with `resume_score` populated
  - Assert detail endpoint returns `200` with `resume_report` populated
  - Assert detail endpoint returns `404` for a random UUID
  - Clean up seeded rows after assertions
  - _Requirements: 1.1, 1.3, 1.4, 2.1, 2.2, 2.5_

- [x] 4.2 Write unit tests for session list and detail handlers


  - Use `pytest-asyncio` and `unittest.mock.AsyncMock` to mock the `asyncpg` connection
  - Cover: empty session list, list with mixed statuses, detail found, detail not found, DB error on both endpoints
  - _Requirements: 1.2, 1.4, 2.2, 2.3, 2.4, 3.5_
