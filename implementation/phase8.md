# Phase 8: Real-Time Session Watchdogs & Interactive Guardrails

## 1. Objective
Port the native real-time watchdog loops into the Python LiveKit voice worker session thread. These background tasks monitor candidate behavioral metrics (extended silence and camera feed toggling) to deliver interactive audio warnings and enforce session management policies automatically.

## 2. Guardrail Logic Models

### 2.1. Component A: 60-Second Silence Watchdog
- **Task Design**: Run a concurrent `asyncio` background loop that monitors timestamps of the candidate's last spoken utterance.
- **First-Tier Warning Trigger**: If the candidate remains silent for 60 consecutive seconds, the agent triggers an immediate audio intervention prompt via the LLM/TTS engine: *"Just checking — John, are you still there?"*
- **Grace Window & Expiration**: Start a strict 30-second countdown instantly following the warning. If the candidate speaks, reset the timer. If the candidate remains silent through the grace window, the agent delivers a polite closing sentence and disconnects from the room, updating the session with `end_reason = "silence_timeout"`.

### 2.2. Component B: Camera Track Monitor & Fraud Deterrent
- **Task Design**: Register event listeners for WebRTC track updates inside the LiveKit room session space. Listen directly for `track_muted` and `track_unmuted` events associated with the candidate's video track.
- **Interruption Guard**: When a candidate mutes their camera feed:
  1. Instantly pause the 60-second silence timer tracker to prevent overlaps.
  2. Call `agent.interrupt()` immediately to stop any current agent audio text or speech rendering in the room.
  3. Deliver an explicit camera warning message via the TTS engine: *"John, it looks like your camera was turned off. Please keep your video active to continue the practice session."*
- **Warning Escalation Escalator**: Track cumulative violations across the session lifetime:
  - **Warning 1**: Sent instantly at 15 seconds post-mute.
  - **Warning 2**: Sent at 20 seconds post-mute.
  - **Warning 3**: Sent at 5 seconds post-mute (final notice).
  - **Termination Enforcements**: If the video feed stays off through Warning 3, or if the candidate explicitly toggles their video feed off and on 5 or more times during the session, terminate the call with `end_reason = "disciplinary"`.

### 2.3. Component C: Connection Dropout Recovery Monitor
- **Task Design**: Subscribe to room connectivity status metrics.
- **Behavior**: On receiving a `QUALITY_LOST` or a network disconnection event from the client, pause all active countdown watchdogs. Await reconnection for a maximum window of 60 seconds. If the candidate fails to reconnect within the window, terminate the loop session cleanly with `end_reason = "candidate_leave"`.

---

## 3. Integration Structure Template
Ensure Kiro spins these up within task groupings inside your main room session block:

```python
import asyncio
from livekit.agents import JobContext

async def start_mock_interview(ctx: JobContext, metadata: dict):
    # Establish local tracking states
    session_state = {
        "last_candidate_speech_time": asyncio.get_event_loop().time(),
        "camera_mute_count": 0,
        "is_camera_active": True
    }

    # Spin up background guardrails concurrently
    silence_task = asyncio.create_task(run_silence_watchdog(ctx, session_state))
    camera_task = asyncio.create_task(run_camera_monitor(ctx, session_state))

    try:
        # Run primary interview question loops here
        ...
    finally:
        # Guarantee cleanup on termination
        silence_task.cancel()
        camera_task.cancel()
        await asyncio.gather(silence_task, camera_task, return_exceptions=True)


4. Verification Check Constraints
The Kiro agent must verify successful completion by asserting mock track state mutations:

Simulate a remote track mute event within a local test execution loop and confirm that any current agent speech text is interrupted instantly.

Verify that watchdog cancellations execute safely during session closures without dropping trace errors or memory leaks into the main process thread loop.