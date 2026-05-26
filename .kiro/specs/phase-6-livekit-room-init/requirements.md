# Requirements Document

## Introduction

Phase 6 introduces the LiveKit Room Initialization endpoint — the backend route the frontend calls when a candidate clicks "Start Interview". The system validates that the session's async processing pipeline has completed, assembles a structured room metadata payload containing all interview context, provisions a WebRTC room via the LiveKit server SDK, issues a signed JWT access token to the client, and advances the session status to `interviewing`. This phase bridges the pre-interview preparation state with the real-time AI voice interview.

## Glossary

- **LiveKit**: An open-source WebRTC SFU (Selective Forwarding Unit) server used to host real-time audio/video rooms.
- **RoomServiceClient**: The LiveKit Python SDK client used to create and manage rooms on the LiveKit server.
- **AccessToken**: A signed JWT issued by the LiveKit Python SDK that grants a participant permission to join a specific room.
- **Room Metadata**: A JSON string injected into a LiveKit room at creation time, readable by all participants including the AI voice agent worker.
- **Practice Session**: A database record in `practice_sessions` representing one candidate interview attempt, identified by a UUID.
- **Session Status**: A string field on `practice_sessions` tracking pipeline progress. Valid values: `parsing`, `scoring`, `ready_to_start`, `interviewing`, `completed`.
- **Agent Blueprint**: The room metadata payload that the LiveKit voice agent worker reads to configure itself for the interview.
- **LIVEKIT_API_URL**: Environment variable holding the LiveKit server URL (e.g., `http://localhost:7880`).
- **LIVEKIT_API_KEY**: Environment variable holding the LiveKit API key for server-side authentication.
- **LIVEKIT_API_SECRET**: Environment variable holding the LiveKit API secret for signing access tokens.
- **Start Endpoint**: The `POST /api/v1/practice/session/{session_id}/start` route defined in this phase.
- **Room Name**: A deterministic string derived from the session ID, formatted as `practice-room-{session_id}`.
- **livekit-api**: The official LiveKit Python SDK package used for room provisioning and token generation.

---

## Requirements

### Requirement 1

**User Story:** As a candidate, I want the system to validate my session is ready before starting the interview, so that I am not placed into a broken or incomplete room.

#### Acceptance Criteria

1. WHEN the Start Endpoint receives a request with a `session_id`, THE System SHALL query the `practice_sessions` table and verify the record exists and belongs to the authenticated user.
2. IF the `practice_sessions` record does not exist or belongs to a different user, THEN THE System SHALL return an HTTP 404 response with a descriptive error message.
3. IF the `status` field of the `practice_sessions` record is `parsing` or `scoring`, THEN THE System SHALL return an HTTP 400 response with the message indicating that background processing is not yet complete.
4. IF the `status` field of the `practice_sessions` record is `interviewing` or `completed`, THEN THE System SHALL return an HTTP 400 response indicating the session has already been started or finished.
5. WHEN the `status` field of the `practice_sessions` record is `ready_to_start`, THE System SHALL proceed to room provisioning.

---

### Requirement 2

**User Story:** As the AI voice agent, I want to receive a complete structured metadata payload when I join the room, so that I can conduct a fully personalized interview without additional database lookups.

#### Acceptance Criteria

1. WHEN the session status is `ready_to_start`, THE System SHALL assemble a room metadata JSON object containing: `interview_id`, `user_id`, `candidate_name`, `job_title`, `questions`, `resume_summary`, `jd_summary`, `agent_name`, `agent_voice`, `agent_language`, and `agent_gender`.
2. WHEN assembling the metadata, THE System SHALL populate `questions` from the `generated_questions` JSONB column of the `practice_sessions` record, serialized as an array of question objects.
3. WHEN assembling the metadata, THE System SHALL populate `resume_summary` from the `resume_report` JSONB column and `jd_summary` from the `description` column of the associated `practice_jobs` record.
4. WHEN assembling the metadata, THE System SHALL set `agent_name` to `"Aria"`, `agent_voice` to `"simran"`, `agent_language` to `"English"`, and `agent_gender` to `"F"` as fixed configuration values.
5. THE System SHALL serialize the assembled metadata dictionary as a UTF-8 JSON string before injecting it into the LiveKit room.

---

### Requirement 3

**User Story:** As a candidate, I want a LiveKit room to be provisioned with my interview context, so that the AI voice agent can join the same room and conduct my interview.

#### Acceptance Criteria

1. WHEN the metadata payload is assembled, THE System SHALL use the `RoomServiceClient` from the `livekit-api` SDK to create a room named `practice-room-{session_id}` on the LiveKit server configured via `LIVEKIT_API_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET`.
2. WHEN creating the room, THE System SHALL inject the serialized metadata JSON string into the room's metadata property.
3. IF the LiveKit server is unreachable or returns an error during room creation, THEN THE System SHALL return an HTTP 503 response with a descriptive error message and SHALL NOT update the session status.
4. WHEN the room is successfully created, THE System SHALL update the `livekit_room_name` column of the `practice_sessions` record to `practice-room-{session_id}`.

---

### Requirement 4

**User Story:** As a candidate, I want to receive a signed LiveKit access token, so that my browser client can authenticate and join the interview room.

#### Acceptance Criteria

1. WHEN the room is provisioned, THE System SHALL instantiate an `AccessToken` using `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET` from the `livekit-api` SDK.
2. WHEN configuring the token, THE System SHALL set the token identity to the candidate's `user_id` string and set the room name to `practice-room-{session_id}`.
3. WHEN configuring the token grants, THE System SHALL enable `room_join=True`, `can_publish=True`, and `can_subscribe=True`.
4. THE System SHALL generate the signed JWT string from the configured `AccessToken` instance.
5. WHEN the token is generated, THE System SHALL update the `practice_sessions` record status to `interviewing`.

---

### Requirement 5

**User Story:** As a candidate, I want the start endpoint to return all connection details in a single response, so that my frontend can immediately connect to the interview room.

#### Acceptance Criteria

1. WHEN room provisioning and token generation succeed, THE System SHALL return an HTTP 201 response containing: `livekit_token`, `livekit_url`, `room_name`, and `status`.
2. WHEN constructing the response, THE System SHALL set `livekit_url` to the value of the `LIVEKIT_API_URL` environment variable.
3. WHEN constructing the response, THE System SHALL set `room_name` to `practice-room-{session_id}` and `status` to `"interviewing"`.
4. WHEN the same `session_id` is submitted to the Start Endpoint and the session status is already `interviewing`, THE System SHALL return an HTTP 400 response rather than creating a duplicate room.

---

### Requirement 6

**User Story:** As a developer, I want the LiveKit credentials and URL to be loaded from environment variables, so that the application can connect to different LiveKit instances across environments without code changes.

#### Acceptance Criteria

1. THE System SHALL load `LIVEKIT_API_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET` from the application's environment configuration via the `Settings` class in `config.py`.
2. IF any of `LIVEKIT_API_KEY` or `LIVEKIT_API_SECRET` are absent from the environment, THEN THE System SHALL raise a configuration validation error at application startup.
3. THE System SHALL use the `livekit-api` Python package for all LiveKit server interactions and token generation.
