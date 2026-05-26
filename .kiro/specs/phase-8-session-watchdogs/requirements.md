# Requirements Document

## Introduction

Phase 8 extends the LiveKit voice agent worker (Phase 7) with three concurrent real-time guardrail systems that run inside the active interview session. These watchdogs monitor candidate behavior — silence duration, camera feed state, and network connectivity — and enforce session management policies through audio warnings and controlled termination. The guardrails protect session integrity, deter dishonest behavior, and ensure the transcript collected for Phase 9 reflects a genuine, complete interview attempt.

## Glossary

- **Agent**: The Python LiveKit voice worker process (`agent.py`) running the Aria AI interviewer.
- **Candidate**: The single user participating in the mock interview session via WebRTC.
- **Session State**: A shared in-memory dictionary tracking per-session behavioral metrics (last speech time, camera mute count, camera active flag).
- **Silence Watchdog**: An `asyncio` background task that monitors elapsed time since the candidate's last spoken utterance.
- **Camera Monitor**: An `asyncio` background task that listens for WebRTC video track mute/unmute events from the candidate.
- **Dropout Monitor**: An `asyncio` background task that listens for room connectivity loss events.
- **Grace Window**: A 30-second countdown period following a silence warning during which the candidate may resume speaking to reset the timer.
- **end_reason**: A string field written to the session record indicating why the interview session terminated (values: `"normal"`, `"silence_timeout"`, `"disciplinary"`, `"candidate_leave"`).
- **VoicePipelineAgent**: The LiveKit SDK class orchestrating STT, LLM, and TTS in the voice pipeline.
- **asyncio task**: A concurrent coroutine scheduled via `asyncio.create_task()` running alongside the main interview loop.

---

## Requirements

### Requirement 1: Concurrent Watchdog Lifecycle Management

**User Story:** As a system operator, I want all watchdog tasks to start with the interview and be guaranteed to clean up on session end, so that no orphaned background tasks leak into the worker process.

#### Acceptance Criteria

1. WHEN the `start_mock_interview` function is called, THE Agent SHALL create and start the silence watchdog, camera monitor, and dropout monitor as concurrent `asyncio` tasks before the interview greeting is delivered.
2. WHEN the interview session ends for any reason, THE Agent SHALL cancel all active watchdog tasks and await their completion using `asyncio.gather` with `return_exceptions=True` inside a `finally` block.
3. THE Agent SHALL maintain a `session_state` dictionary shared across all watchdog tasks containing at minimum: `last_candidate_speech_time`, `camera_mute_count`, and `is_camera_active`.
4. WHEN a watchdog task is cancelled, THE Agent SHALL suppress `asyncio.CancelledError` without logging it as an unhandled exception.

---

### Requirement 2: Silence Watchdog — First-Tier Warning

**User Story:** As a candidate, I want to receive an audio check-in prompt if I go silent for too long, so that I know the session is still active and I can resume speaking.

#### Acceptance Criteria

1. WHEN the candidate has not produced a speech utterance for 60 consecutive seconds, THE Silence Watchdog SHALL trigger the VoicePipelineAgent to deliver an audio warning message addressed to the candidate by name.
2. WHILE the silence watchdog loop is running, THE Agent SHALL update `session_state["last_candidate_speech_time"]` each time the candidate's STT produces a recognized utterance.
3. THE Silence Watchdog SHALL poll the elapsed silence duration at an interval no greater than 5 seconds to detect the 60-second threshold.
4. WHEN the first-tier warning is delivered, THE Silence Watchdog SHALL immediately start a 30-second grace window countdown.

---

### Requirement 3: Silence Watchdog — Grace Window & Termination

**User Story:** As a candidate, I want the session to give me a 30-second window to respond after a silence warning before terminating, so that brief technical pauses do not unfairly end my session.

#### Acceptance Criteria

1. WHEN the 30-second grace window expires without a candidate utterance, THE Silence Watchdog SHALL instruct the VoicePipelineAgent to deliver a polite closing message and then disconnect from the LiveKit room.
2. WHEN the candidate speaks during the grace window, THE Silence Watchdog SHALL reset the silence timer and cancel the grace window countdown, resuming normal monitoring.
3. WHEN the session is terminated by the silence watchdog, THE Agent SHALL record `end_reason` as `"silence_timeout"` in the session termination payload passed to Phase 9.
4. IF the camera monitor has paused the silence timer, THEN THE Silence Watchdog SHALL NOT advance the silence elapsed counter until the camera monitor explicitly resumes it.

---

### Requirement 4: Camera Monitor — Mute Detection & Immediate Response

**User Story:** As a session integrity enforcer, I want the agent to immediately interrupt its speech and warn the candidate when their camera is turned off, so that the session cannot proceed without video.

#### Acceptance Criteria

1. WHEN the candidate's video track emits a `track_muted` event, THE Camera Monitor SHALL immediately call `agent.interrupt()` to stop any in-progress TTS audio output.
2. WHEN the candidate's video track emits a `track_muted` event, THE Camera Monitor SHALL pause the silence watchdog timer by setting a pause flag in `session_state`.
3. WHEN the candidate's video track emits a `track_muted` event, THE Camera Monitor SHALL increment `session_state["camera_mute_count"]` by 1.
4. WHEN the candidate's video track emits a `track_unmuted` event, THE Camera Monitor SHALL resume the silence watchdog timer and reset the per-mute warning escalation state.

---

### Requirement 5: Camera Monitor — Warning Escalation Sequence

**User Story:** As a session integrity enforcer, I want escalating audio warnings delivered at defined intervals after a camera mute, so that the candidate has clear notice before the session is terminated.

#### Acceptance Criteria

1. WHEN the candidate's camera has been muted for 15 seconds, THE Camera Monitor SHALL deliver Warning 1 via the TTS engine instructing the candidate to re-enable their video.
2. WHEN the candidate's camera has been muted for 20 seconds after Warning 1, THE Camera Monitor SHALL deliver Warning 2 via the TTS engine with an escalated message.
3. WHEN the candidate's camera has been muted for 5 seconds after Warning 2, THE Camera Monitor SHALL deliver Warning 3 as a final notice via the TTS engine.
4. WHEN Warning 3 expires without the candidate re-enabling their camera, THE Camera Monitor SHALL terminate the session with `end_reason` set to `"disciplinary"`.
5. WHEN `session_state["camera_mute_count"]` reaches 5 or more during the session lifetime, THE Camera Monitor SHALL terminate the session with `end_reason` set to `"disciplinary"` regardless of current camera state.

---

### Requirement 6: Connection Dropout Monitor

**User Story:** As a candidate, I want the session to pause watchdog timers and wait for me to reconnect if I lose network connectivity, so that a brief dropout does not unfairly terminate my session.

#### Acceptance Criteria

1. WHEN a room connectivity loss or `QUALITY_LOST` event is detected, THE Dropout Monitor SHALL pause all active countdown timers in the silence watchdog and camera monitor.
2. WHEN a room connectivity loss event is detected, THE Dropout Monitor SHALL begin a 60-second reconnection window.
3. WHEN the candidate reconnects within the 60-second window, THE Dropout Monitor SHALL resume all paused watchdog timers from their pre-dropout state.
4. WHEN the 60-second reconnection window expires without the candidate reconnecting, THE Dropout Monitor SHALL terminate the session with `end_reason` set to `"candidate_leave"`.

---

### Requirement 7: Session Termination Handoff

**User Story:** As the Phase 9 pipeline, I want the agent to always produce a structured termination payload regardless of how the session ends, so that the transcript webhook receives consistent data.

#### Acceptance Criteria

1. WHEN any watchdog triggers a session termination, THE Agent SHALL collect the current chat history, filter out system-role messages, and assemble a transcript array before disconnecting.
2. THE Agent SHALL pass the assembled transcript array and the `end_reason` string to the Phase 9 webhook dispatch function (to be implemented in Phase 9).
3. WHEN the session ends normally (all 8 questions answered), THE Agent SHALL record `end_reason` as `"normal"` in the termination payload.
4. IF the transcript array is empty at termination time, THEN THE Agent SHALL still dispatch the webhook payload with an empty transcript array rather than suppressing the call.
