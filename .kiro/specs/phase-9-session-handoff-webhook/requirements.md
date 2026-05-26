# Requirements Document

## Introduction

Phase 9 implements the secure handoff bridge between the Python LiveKit voice agent worker and the FastAPI backend. When an interview session ends — whether normally or via a watchdog-triggered termination — the agent compiles the full transcript, applies crash-recovery logic for any dropped final utterances, and fires a synchronous HTTP POST to the backend webhook. The backend endpoint validates the payload, persists the transcript and session metadata to the database, advances the session status to `interview_processing`, and immediately enqueues the Phase 10 grading pipeline as a background task.

## Glossary

- **Agent Worker**: The standalone Python process running `agent.py` that drives the LiveKit voice interview pipeline.
- **Webhook Endpoint**: The FastAPI route `POST /api/v1/practice/session/complete` that receives the session handoff payload from the Agent Worker.
- **Session**: A row in the `practice_sessions` PostgreSQL table identified by a UUID `session_id`.
- **Transcript**: An ordered array of dialogue turns, each containing a `speaker` label (`"agent"` or `"candidate"`), the spoken `text`, and a `created_at` Unix timestamp.
- **Recovered Turn**: A transcript turn that was present in the agent's internal history cache but was not committed to the main chat context stream before the session ended, marked with `recovered = true`.
- **End Reason**: A string enum value describing why the session terminated: `"normal"`, `"silence_timeout"`, `"disciplinary"`, or `"candidate_leave"`.
- **BackgroundTasks**: FastAPI's native `BackgroundTasks` utility used to enqueue the Phase 10 grading pipeline without blocking the HTTP response.
- **interview_processing**: The `practice_sessions.status` value that signals the session transcript has been received and the grading pipeline has been triggered.
- **SessionCompletePayload**: The Pydantic v2 request body schema for the webhook endpoint.
- **TranscriptTurn**: A single Pydantic v2 model representing one dialogue turn within the transcript array.

---

## Requirements

### Requirement 1

**User Story:** As the Agent Worker, I want to compile a clean transcript from the chat context when the session ends, so that no dialogue turns are lost before the handoff.

#### Acceptance Criteria

1. WHEN the interview session loop terminates for any reason, THE Agent Worker SHALL execute the transcript compilation logic inside a `finally` block to guarantee execution regardless of how the session ended.
2. WHEN compiling the transcript, THE Agent Worker SHALL iterate over all messages in the chat context and exclude any message whose role is `"system"`.
3. WHEN mapping chat context roles to transcript speaker labels, THE Agent Worker SHALL assign the label `"agent"` to messages with role `"assistant"` and the label `"candidate"` to all other non-system messages.
4. WHEN a chat context message contains a list of content parts rather than a plain string, THE Agent Worker SHALL flatten the parts into a single space-joined string before storing the `text` field.

---

### Requirement 2

**User Story:** As the Agent Worker, I want to detect and recover any final assistant utterance that was dropped mid-delivery, so that the grading pipeline receives a complete record of what the agent said.

#### Acceptance Criteria

1. WHEN the session ends and the last message in the agent's internal history cache has role `"assistant"` and that message is absent from the compiled transcript array, THE Agent Worker SHALL append that message to the transcript array as a recovered turn.
2. WHEN appending a recovered turn, THE Agent Worker SHALL include the field `recovered` set to `true` in the turn object alongside the standard `speaker`, `text`, and `created_at` fields.
3. WHEN the last cached assistant message is already present in the compiled transcript, THE Agent Worker SHALL NOT append a duplicate recovered turn.

---

### Requirement 3

**User Story:** As the Agent Worker, I want to dispatch the compiled session data to the backend webhook, so that the backend can persist the transcript and trigger grading.

#### Acceptance Criteria

1. WHEN the transcript compilation is complete, THE Agent Worker SHALL make a synchronous HTTP POST request to the configured `BACKEND_URL` at path `/api/v1/practice/session/complete`.
2. WHEN constructing the POST request body, THE Agent Worker SHALL include the fields `session_id`, `end_reason`, `duration_seconds`, and `transcript` as defined in the `SessionCompletePayload` schema.
3. WHEN the HTTP POST request returns a non-2xx status code, THE Agent Worker SHALL log the status code and response body at `ERROR` level and SHALL NOT raise an unhandled exception that would crash the agent process.
4. WHEN the HTTP POST request raises a network-level exception, THE Agent Worker SHALL catch the exception, log it at `ERROR` level, and allow the agent process to exit cleanly.
5. WHILE the agent process is inside the `finally` block, THE Agent Worker SHALL complete the webhook dispatch before the process exits.

---

### Requirement 4

**User Story:** As the FastAPI backend, I want a webhook endpoint that validates the incoming session handoff payload, so that malformed or unauthorized data is rejected before touching the database.

#### Acceptance Criteria

1. THE Webhook Endpoint SHALL accept HTTP POST requests at the path `/api/v1/practice/session/complete`.
2. WHEN the request body does not conform to the `SessionCompletePayload` schema, THE Webhook Endpoint SHALL return HTTP 422 Unprocessable Entity without executing any database operations.
3. WHEN the `transcript` field in the request body is an empty array, THE Webhook Endpoint SHALL return HTTP 422 Unprocessable Entity.
4. WHEN the `session_id` in the payload does not match any row in the `practice_sessions` table, THE Webhook Endpoint SHALL return HTTP 404 Not Found.
5. WHEN the matched session row has a `status` value other than `"interviewing"`, THE Webhook Endpoint SHALL return HTTP 409 Conflict.

---

### Requirement 5

**User Story:** As the FastAPI backend, I want to persist the transcript and session metadata atomically, so that the database is never left in a partially updated state.

#### Acceptance Criteria

1. WHEN the payload passes all validation checks, THE Webhook Endpoint SHALL write the `transcript` array to the `practice_sessions.transcript` JSONB column.
2. WHEN persisting the session data, THE Webhook Endpoint SHALL update the `end_reason` column with the value from the payload.
3. WHEN persisting the session data, THE Webhook Endpoint SHALL update the `duration_seconds` column with the value from the payload.
4. WHEN persisting the session data, THE Webhook Endpoint SHALL advance the `practice_sessions.status` column from `"interviewing"` to `"interview_processing"` in the same database operation.
5. IF a database error occurs during the update, THEN THE Webhook Endpoint SHALL return HTTP 500 Internal Server Error and SHALL NOT trigger the Phase 10 grading background task.

---

### Requirement 6

**User Story:** As the FastAPI backend, I want to immediately enqueue the Phase 10 grading pipeline after persisting the transcript, so that assessment processing begins without delaying the agent's response.

#### Acceptance Criteria

1. WHEN the database update completes successfully, THE Webhook Endpoint SHALL inject FastAPI's native `BackgroundTasks` handler to enqueue the Phase 10 grading pipeline function.
2. WHEN enqueuing the background task, THE Webhook Endpoint SHALL pass the `session_id` as the sole argument to the grading pipeline function.
3. WHEN the background task has been enqueued, THE Webhook Endpoint SHALL return HTTP 200 OK with a JSON body containing a `status` field set to `"received"` and a `session_id` field.
4. THE Webhook Endpoint SHALL return the HTTP 200 response before the Phase 10 grading pipeline completes execution.

---

### Requirement 7

**User Story:** As a developer, I want the webhook request and response shapes defined as strict Pydantic v2 models, so that the contract between the agent and backend is enforced at runtime.

#### Acceptance Criteria

1. THE system SHALL define a `TranscriptTurn` Pydantic v2 model with required fields: `speaker` (literal `"agent"` or `"candidate"`), `text` (non-empty string), and `created_at` (float), and an optional `recovered` field (bool, default `False`).
2. THE system SHALL define a `SessionCompletePayload` Pydantic v2 model with required fields: `session_id` (UUID), `end_reason` (string), `duration_seconds` (non-negative integer), and `transcript` (list of `TranscriptTurn` with minimum length 1).
3. THE system SHALL define a `SessionCompleteResponse` Pydantic v2 model with fields: `status` (string) and `session_id` (UUID).
4. WHERE the `end_reason` field is provided, THE `SessionCompletePayload` SHALL validate that the value is one of: `"normal"`, `"silence_timeout"`, `"disciplinary"`, or `"candidate_leave"`.
