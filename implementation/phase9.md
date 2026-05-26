# Phase 9: Session Handoff & Transcript Recovery Webhook

## 1. Objective
Build the secure handoff bridge between the Python audio worker agent and the FastAPI backend. This phase implements the transcript aggregation and crash-recovery logic inside the agent, alongside the endpoint on the main server that accepts the payload and flags the session for grading.

## 2. Technical Requirements
- **HTTP Method**: `POST`
- **Route Path**: `/api/v1/practice/session/complete`
- **Communication Pattern**: Synchronous internal HTTP request fired from the Python agent worker process directly to the FastAPI server instance.

---

## 3. Operational Step-by-Step Logic

### 3.1. Agent-Side Transcript Compilation & Fallback Recovery
When the interview loop terminates (whether normally or via a watchdog timeout), the agent worker must execute this collection sequence inside an infallible `finally:` block:
1. **Dialogue Extraction**: Iterate over the session messages, filtering out `system` instructions to build a clean array of candidate and agent turns.
2. **Crash & Cutoff Recovery**: If the session dropped suddenly mid-TTS delivery or crashed right as the agent was speaking, look at the internal history cache. If the last assistant statement exists in the cache but didn't make it to the main stream, manually append it to the transcript array marked explicitly as `recovered = true`. This prevents data loss for your grading pipeline.
3. **Webhook Post**: Make a synchronous POST request containing the compiled transcript array, session ID, total duration, and explicit termination reason.

### 3.2. Backend-Side Webhook Processing Router
The FastAPI endpoint must handle the incoming payload instantly:
1. **Verification**: Match the incoming `session_id` against the database and ensure the current status is `'interviewing'`.
2. **Data Commit**: 
   - Serialize and write the incoming array directly into the `transcript` column of the `practice_sessions` table.
   - Update `end_reason` and `duration_seconds` using fields sent by the agent.
   - Advance the tracking state flag to `'interview_processing'`.
3. **Trigger Evaluation**: Immediately inject FastAPI's native `BackgroundTasks` handler to kick off the Phase 10 grading and evaluation pipeline asynchronously.
4. **Respond Quickly**: Return a simple `200 OK` JSON confirmation payload back to the agent worker so it can disconnect from the room cleanly.

---

## 4. Expected Webhook Request Payload Schema
```json
{
  "session_id": "d3c2b1a0-9f8e-7d6c-5b4a-3f2e1d0c9b8a",
  "end_reason": "normal",
  "duration_seconds": 654,
  "transcript": [
    {
      "speaker": "agent",
      "text": "Hi John, let's start with your Python background.",
      "created_at": 1716305410.5
    },
    {
      "speaker": "candidate",
      "text": "Sure, I have been building FastAPI apps for about two years...",
      "created_at": 1716305422.1
    }
  ]
}

5. Verification Check ConstraintsThe Kiro agent must verify successful completion by asserting data payloads:Simulate a mock payload post to /api/v1/practice/session/complete and confirm it mutates the PostgreSQL database row from 'interviewing' $\rightarrow$ 'interview_processing' flawlessly.Confirm that formatting abnormalities or empty transcripts sent to the webhook are caught cleanly with an HTTP 422 Unprocessable Entity rather than causing internal database connection hangs.

