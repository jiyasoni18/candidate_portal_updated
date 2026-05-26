# Phase 6: LiveKit Room Initialization & Metadata Injection Router

## 1. Objective
Build the endpoint that the frontend calls when the candidate clicks "Start Interview". This route validates the session state, builds the unified room metadata payload, spins up a virtual WebRTC channel via the LiveKit server, and issues a secure access token back to the client.

## 2. Infrastructure Setup & Environment Variables
Ensure Kiro understands that the backend needs the following environment keys to connect to your local LiveKit Docker container instance:
- `LIVEKIT_API_URL`: (e.g., `http://localhost:7880` or `wss://...`)
- `LIVEKIT_API_KEY`: Your secret LiveKit developer key.
- `LIVEKIT_API_SECRET`: Your secret LiveKit developer signature token.

---

## 3. Tech Stack Requirements (FastAPI + livekit-api SDK)
- **HTTP Method**: `POST`
- **Route Path**: `/api/v1/practice/session/{session_id}/start`
- **Backend Dependency**: Injects the active session database manager to verify records.

---

## 4. Operational Step-by-Step Backend Logic

### 4.1. Validate Session State
1. Lookup the `practice_session` by its ID and ensure it belongs to the authenticated user.
2. Verify that the `status` is exactly `'ready_to_start'`. If the background pipeline from Phase 4 is still working (`'parsing'` or `'scoring'`), return an HTTP `400 Bad Request` explaining that processing is not yet complete.

### 4.2. Serialize Room Metadata (The Core Agent Blueprint)
Compile your structural context dictionary into a single, clean JSON string to inject as the room's global metadata property. This payload must match your old system's structure exactly so your voice worker can read it seamlessly:

```json
{
  "interview_id": "d3c2b1a0-9f8e-7d6c-5b4a-3f2e1d0c9b8a",
  "user_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
  "candidate_name": "John Practice Doe",
  "job_title": "Senior React Developer",
  "questions": [
    { "id": 1, "question": "Okay so John, tell me about your background...", "category": "opening", "expected_duration_seconds": 120 }
  ],
  "resume_summary": "Parsed key skills, experience history...",
  "jd_summary": "Raw job description metrics...",
  "agent_name": "Aria",
  "agent_voice": "simran",
  "agent_language": "English",
  "agent_gender": "F"
}


4.3. Room Provisioning & Token Generation
Use LiveKit's RoomServiceClient to create or join a room named dynamically using the session format: practice-room-{session_id}. Inject the serialized metadata string directly into the room initialization parameters.

Initialize an AccessToken instance from the LiveKit SDK.

Configure the token claims grant:

Set identity to the candidate's user ID.

Set the room name destination grant to practice-room-{session_id}.

Enable grants: room_join=True, can_publish=True, can_subscribe=True.

Update the database row: set livekit_room_name to practice-room-{session_id} and advance status strictly to 'interviewing'.

Return the authorization tokens to the UI client.

5. Expected API Payload Response Schema (201 Created)

{
  "livekit_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3...",
  "livekit_url": "ws://localhost:7880",
  "room_name": "practice-room-d3c2b1a0-9f8e-7d6c-5b4a-3f2e1d0c9b8a",
  "status": "interviewing"
}


6. Verification Check Constraints
The Kiro agent must verify successful completion by asserting:

Hit the start endpoint on a verified session, decode the resulting JWT string, and confirm the room grants, identity parameters, and room name scopes align perfectly.

Ensure that if the same session token is initialized twice, it returns the active room mapping rather than breaking state concurrency tracking tables.