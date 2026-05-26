# Implementation Plan — Phase 9: Session Handoff & Transcript Recovery Webhook

- [x] 1. Add Pydantic v2 schema models for the webhook contract





  - Create `schemas/session_complete.py` with `TranscriptTurn`, `SessionCompletePayload`, and `SessionCompleteResponse`
  - `TranscriptTurn`: `speaker` (Literal["agent","candidate"]), `text` (min_length=1), `created_at` (float), `recovered` (bool, default False)
  - `SessionCompletePayload`: `session_id` (UUID), `end_reason` (Literal of 4 values), `duration_seconds` (int, ge=0), `transcript` (list[TranscriptTurn], min_length=1)
  - `SessionCompleteResponse`: `status` (str), `session_id` (UUID)
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [x] 2. Extend the database schema with missing columns





  - Add `end_reason VARCHAR(50)` and `duration_seconds INTEGER` columns to `practice_sessions` in `database/init.sql` using `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`
  - _Requirements: 5.2, 5.3_

- [x] 3. Add `BACKEND_URL` to application config





  - Add `BACKEND_URL: str = "http://localhost:8000"` to the `Settings` class in `config.py`
  - _Requirements: 3.1_

- [x] 4. Implement the webhook endpoint in the practice router





  - Add `POST /practice/session/complete` to `api/routers/practice.py`
  - Query `practice_sessions` by `session_id`; return 404 if not found, 409 if `status != "interviewing"`
  - Execute a single `UPDATE` writing `transcript`, `end_reason`, `duration_seconds`, and `status = 'interview_processing'`; return 500 on `asyncpg.PostgresError`
  - Enqueue `grade_session_background` via `background_tasks.add_task` after a successful DB write
  - Return `SessionCompleteResponse(status="received", session_id=payload.session_id)` with HTTP 200
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4, 5.5, 6.1, 6.2, 6.3, 6.4_
  - [x] 4.1 Write unit tests for the webhook endpoint


    - Test 422 on empty transcript, 404 on unknown session_id, 409 on wrong status, 200 happy path with DB update and background task enqueue
    - _Requirements: 4.2, 4.3, 4.4, 4.5_

- [x] 5. Add `grade_session_background` stub to the background pipeline service




  - Add `async def grade_session_background(session_id: str, db_pool) -> None` to `services/background_pipeline.py` that logs receipt and returns
  - _Requirements: 6.1, 6.2_

- [x] 6. Implement crash-recovery helper and replace the dispatch stub in the agent





  - Add `_apply_recovery(transcript, history_cache) -> list` pure helper to `agent.py`; appends a recovered turn with `recovered=True` only when the last cached assistant message is absent from the compiled transcript
  - Replace `dispatch_session_complete` stub with a real `httpx.AsyncClient` POST to `{settings.BACKEND_URL}/api/v1/practice/session/complete`; catch all exceptions and log at ERROR without re-raising
  - Extend `dispatch_session_complete` signature to accept `duration_seconds: int`
  - _Requirements: 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 3.4_

- [x] 7. Wire duration tracking and recovery into `start_mock_interview`





  - Capture `session_start_time = time.time()` at the top of `start_mock_interview`
  - In the `finally` block, call `_apply_recovery(transcript, agent.chat_ctx.messages)` after `_collect_transcript`
  - Compute `duration_seconds = int(time.time() - session_start_time)` and pass it to `dispatch_session_complete`
  - _Requirements: 1.1, 2.1, 3.2, 3.5_
  - [x] 7.1 Write unit tests for agent-side helpers

    - Test `_apply_recovery` appends recovered turn when last cached message is absent; test no duplicate when already present
    - Test `dispatch_session_complete` logs error on non-2xx and on network exception without raising
    - _Requirements: 2.1, 2.2, 2.3, 3.3, 3.4_
