# End-to-End Testing Guide

This guide walks you through fully testing the Candidate Practice Portal — from spinning up every service to verifying the complete user flow.

---

## Prerequisites

Make sure you have these installed and available:

- Docker Desktop (running)
- Python 3.11+ with `uv` / `pip`
- Node.js 18+
- A terminal for each service (4 total)

---

## Step 1 — Start the Database (Docker)

The backend expects PostgreSQL on port `5434`.

```bash
docker compose up -d
```

Verify it's healthy:

```bash
docker ps
```

You should see the `interview_practice_db` container running. If you need to reset the schema:

```bash
docker exec -i <container_name> psql -U practice_user -d interview_practice_db < database/init.sql
```

---

## Step 2 — Start the FastAPI Backend

Open terminal 1. Activate the virtual environment first.

```bash
# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

Then start the server:

```bash
uvicorn main:app --reload --port 8000
```

Confirm it's up by visiting: http://localhost:8000/docs

You should see the Swagger UI with the `/api/v1/practice/...` routes listed.

---

## Step 3 — Start the LiveKit Voice Agent Worker

Open terminal 2. Same virtual environment.

```bash
.venv\Scripts\activate   # Windows
# or
source .venv/bin/activate

python agent.py start
```

The agent connects to your LiveKit Cloud project using the credentials in `.env` (`LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `LIVEKIT_URL`). You should see log output like:

```
INFO  Connected to LiveKit server
INFO  Waiting for room assignments...
```

If you see auth errors, double-check the keys in `.env` match your LiveKit Cloud dashboard.

---

## Step 4 — Start the Next.js Frontend

Open terminal 3.

```bash
cd frontend
npm install   # only needed first time
npm run dev
```

Frontend runs at: http://localhost:3000

---

## Step 5 — Run the Automated Test Suites

### Backend (pytest)

Open terminal 4. From the project root with the venv active:

```bash
pytest tests/ -v
```

Key test files and what they cover:

| File | Covers |
|---|---|
| `tests/test_practice_initialize.py` | Session init endpoint, file upload, DB writes |
| `tests/test_phase5_endpoints.py` | Session list + detail polling endpoints |
| `tests/test_phase6_start.py` | LiveKit room provisioning + token generation |
| `tests/test_phase6_schemas.py` | Pydantic schema validation for LiveKit payloads |
| `tests/test_livekit_helper.py` | LiveKit helper functions |
| `tests/test_phase8_watchdogs.py` | Silence, camera, and dropout watchdog logic |
| `tests/test_phase9_webhook.py` | Session complete webhook + transcript persistence |
| `tests/test_phase10_grading.py` | Post-interview grading pipeline |
| `tests/test_agent_prompt.py` | Aria system prompt builder |
| `tests/test_background_pipeline.py` | Async resume parsing + scoring pipeline |
| `tests/test_config_validation.py` | Environment config validation |

### Frontend (vitest)

```bash
cd frontend
npm test
```

Key test files:

| File | Covers |
|---|---|
| `__tests__/AssessmentPage.test.tsx` | Post-interview assessment page, polling, all score dimensions |
| `__tests__/PracticeSessionPage.test.tsx` | Resume report polling page |
| `__tests__/InterviewStudioPage.test.tsx` | LiveKit interview room page |
| `__tests__/MediaPreCheck.test.tsx` | Camera/mic pre-check component |
| `__tests__/NewSessionModal.test.tsx` | Upload form modal |
| `__tests__/SessionGrid.test.tsx` | Dashboard session list |
| `__tests__/StatusBadge.test.tsx` | Status badge component |

---

## Step 6 — Manual End-to-End Flow

With all 3 services running (backend, agent, frontend), walk through this flow in the browser.

### 6.1 Create a Practice Session

1. Go to http://localhost:3000/dashboard
2. Click "New Practice Session"
3. Upload a PDF resume
4. Paste a job description into the text area
5. Click Submit

You should be redirected to `/practice/<session_id>` and see the processing spinner.

### 6.2 Wait for Resume Analysis

The page polls every 3 seconds. Watch the status badge cycle through:

```
parsing → scoring → ready_to_start
```

Once `ready_to_start`, the Resume Alignment Report renders with:
- A score out of 100
- Core Strengths list
- Preparation Gaps list

### 6.3 Enter the Interview Room

Click "Enter AI Practice Interview Booth". You land on `/interview/<session_id>`.

1. The MediaPreCheck component asks for camera and microphone permissions — grant both
2. Click "Start Interview"
3. The backend provisions a LiveKit room and returns a token
4. The frontend connects to the WebRTC room
5. Aria (the voice agent) greets you and begins the interview

You should hear Aria's voice within a few seconds. Speak your answers naturally.

### 6.4 Complete the Interview

Aria works through all 8 questions. When done, she closes the session gracefully. The room disconnects and you are redirected to `/practice/<session_id>/assessment`.

### 6.5 Review the Assessment

The assessment page polls until `status === "completed"`. Once ready, you see:

- Overall score (0–100) in a color-coded circle badge
  - ≥80 → emerald
  - ≥68 → indigo
  - ≥52 → amber
  - <52 → red
- Practice verdict label
- Session completion percentage and turns analyzed
- Dimension Breakdown grid (Technical, Role Alignment, Communication, Presence)
- Technical Deep-Dive Probes grid (3 follow-up questions for a real interview)

---

## Step 7 — Verify Watchdog Behaviors (Optional)

These test edge cases in the live interview room.

### Silence Timeout

Stop speaking for 60 seconds. Aria should warn you. If you stay silent for another 30 seconds, she terminates the session with `end_reason: silence_timeout`.

### Camera Off

Mute your video track. Aria interrupts and warns you. Three warnings over ~40 seconds → session terminates with `end_reason: disciplinary`. Turning the camera back on at any point cancels the escalation.

### Dropout / Reconnect

Close the browser tab mid-interview. The agent waits 60 seconds. If you reconnect within that window, the session resumes. After 60 seconds it terminates with `end_reason: candidate_leave`.

---

## Step 8 — Verify the Webhook and Grading Pipeline

After any session ends, check the backend logs (terminal 1) for:

```
POST /api/v1/practice/session/complete  201
```

Then poll the session detail endpoint directly to confirm the pipeline ran:

```bash
curl http://localhost:8000/api/v1/practice/session/<session_id>
```

The `status` field should progress:

```
interviewing → interview_processing → completed
```

And `interview_assessment` should be populated with the full grading payload once `completed`.

---

## Common Issues

**Backend won't start — DB connection refused**
The Docker container isn't running or is on the wrong port. Check `docker ps` and confirm port `5434` is mapped.

**Agent logs "auth error"**
The `LIVEKIT_API_KEY` or `LIVEKIT_API_SECRET` in `.env` doesn't match your LiveKit Cloud project. Copy them from your LiveKit dashboard.

**Frontend can't reach the API**
CORS is configured for `http://localhost:3000` only. Make sure the frontend is running on that exact port and the backend is on `8000`.

**Assessment page stuck on "Generating your assessment scorecard..."**
The grading pipeline is still running or failed silently. Check backend logs for errors from `grade_session_background`. You can also hit the session detail endpoint directly to inspect the current `status`.

**`OPENAI_API_KEY` or `DEEPGRAM_API_KEY` missing**
The voice agent requires both. Add them to `.env` — the agent will fail to start the STT/LLM/TTS pipeline without them.
