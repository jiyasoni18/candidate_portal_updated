# Implementation Plan

- [x] 1. Extend Settings with LiveKit environment variables





  - Add `LIVEKIT_API_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET` fields to the `Settings` class in `config.py`
  - `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET` must have no default value so startup fails fast if absent
  - `LIVEKIT_API_URL` defaults to `"http://localhost:7880"`
  - _Requirements: 6.1, 6.2_

- [x] 2. Add LiveKit Pydantic schemas





- [x] 2.1 Create `schemas/livekit.py` with `RoomMetadataPayload` and `StartSessionResponse` models


  - `RoomMetadataPayload` holds all agent blueprint fields with fixed agent constants as defaults
  - `StartSessionResponse` holds `livekit_token`, `livekit_url`, `room_name`, `status`
  - _Requirements: 2.1, 5.1_

- [x] 2.2 Write unit tests for `RoomMetadataPayload` serialization


  - Verify JSON output matches the expected agent blueprint structure
  - _Requirements: 2.1, 2.5_

- [x] 3. Implement `api/livekit_helper.py`





- [x] 3.1 Implement `provision_room(room_name, metadata)` async function


  - Use `livekit.api.RoomServiceClient` to create the room with metadata injected
  - Wrap blocking SDK call in `asyncio.to_thread`
  - Raise a custom exception on LiveKit server errors
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 3.2 Implement `generate_token(room_name, identity)` async function

  - Instantiate `livekit.api.AccessToken` with `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET`
  - Set identity, room name, and grants: `room_join=True`, `can_publish=True`, `can_subscribe=True`
  - Return the signed JWT string
  - Wrap blocking SDK call in `asyncio.to_thread`
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 3.3 Write unit tests for `livekit_helper` functions


  - Test token claim structure (room, identity, grants) using JWT decode without verification
  - _Requirements: 4.1, 4.2, 4.3_

- [-] 4. Implement the `POST /session/{session_id}/start` endpoint



- [x] 4.1 Add the DB fetch query joining `practice_sessions`, `practice_jobs`, and `users`


  - Single `fetchrow` call that retrieves session status, job title, job description, generated_questions, resume_report, and `users.full_name`
  - Return 404 if row is not found
  - _Requirements: 1.1, 1.2, 2.3_

- [x] 4.2 Implement session status validation logic

  - Return HTTP 400 with status-specific messages for `parsing`, `scoring`, `interviewing`, and `completed`
  - Proceed only when status is `ready_to_start`
  - _Requirements: 1.3, 1.4, 1.5, 5.4_


- [x] 4.3 Assemble `RoomMetadataPayload` and serialize to JSON string

  - Populate all fields from the DB row and fixed agent constants
  - Serialize using `model.model_dump_json()` or `json.dumps(model.model_dump())`
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_



- [x] 4.4 Call `provision_room` and `generate_token`, then update DB and return response

  - Call `provision_room(room_name, metadata_str)` — return HTTP 503 on failure
  - Call `generate_token(room_name, str(user_id))` — return HTTP 503 on failure
  - `UPDATE practice_sessions SET livekit_room_name=$1, status='interviewing' WHERE id=$2`
  - Return `StartSessionResponse` with HTTP 201
  - _Requirements: 3.1, 3.4, 4.5, 5.1, 5.2, 5.3_

- [x] 4.5 Write integration tests in `tests/test_phase6_start.py`


  - Test 404 on unknown session, 400 on each invalid status, 503 path with mocked LiveKit failure
  - _Requirements: 1.2, 1.3, 1.4, 3.3_

- [x] 5. Create verification script `scripts/verify_phase6.py`





  - Hit the start endpoint on a known `ready_to_start` session and assert 201 response shape
  - Decode the JWT and assert `room` and `sub` claims match expected values
  - Assert DB row has `status='interviewing'` and correct `livekit_room_name`
  - Call the endpoint a second time and assert HTTP 400 is returned
  - _Requirements: 1.5, 4.4, 5.1, 5.2, 5.3, 5.4_
