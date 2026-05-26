# Implementation Plan

- [x] 1. Add session_state and transcript helper to agent.py





  - Define the `session_state` dict structure inside `start_mock_interview` with keys: `last_candidate_speech_time`, `camera_mute_count`, `is_camera_active`, `silence_paused`, `end_reason`
  - Implement `_collect_transcript(chat_ctx)` pure helper that filters system messages and maps roles to `"agent"` / `"candidate"` speaker strings
  - Implement `dispatch_session_complete(session_id, end_reason, transcript)` as an async stub that logs a warning without making an HTTP call
  - _Requirements: 1.3, 7.1, 7.2, 7.4_

- [x] 2. Implement the silence watchdog





- [x] 2.1 Implement `run_silence_watchdog` coroutine


  - Poll every 5 seconds; skip elapsed-time advancement when `session_state["silence_paused"]` is True
  - On 60s threshold: call `agent.say()` with the candidate-name-addressed warning, then enter a 30s grace window loop
  - On grace window expiry: call `agent.say()` with closing message, set `end_reason = "silence_timeout"`, call `ctx.room.disconnect()`
  - On candidate speech during grace window: reset timer and return to monitoring state
  - _Requirements: 2.1, 2.3, 2.4, 3.1, 3.2, 3.3, 3.4_

- [x] 2.2 Write unit tests for silence watchdog


  - Mock `session_state` time values and assert warning fires at 60s
  - Assert `ctx.room.disconnect()` is called after grace window expiry
  - Assert timer resets when candidate speaks during grace window
  - _Requirements: 2.1, 3.1, 3.2_

- [x] 3. Implement the camera monitor





- [x] 3.1 Implement `run_camera_monitor` coroutine


  - Register `track_muted` / `track_unmuted` event listeners on `ctx.room`, filtering for `track.kind == "video"`
  - On mute: call `agent.interrupt()`, set `silence_paused = True`, increment `camera_mute_count`; if count ≥ 5 terminate immediately with `end_reason = "disciplinary"`
  - Run escalation sequence: wait 15s → Warning 1, wait 20s → Warning 2, wait 5s → Warning 3; if still muted after Warning 3 terminate with `end_reason = "disciplinary"`
  - On unmute: set `is_camera_active = True`, `silence_paused = False`, cancel current escalation countdown
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 3.2 Write unit tests for camera monitor


  - Simulate `track_muted` event and assert `agent.interrupt()` is called and `silence_paused` is True
  - Assert escalation warnings fire at correct cumulative intervals
  - Assert `end_reason = "disciplinary"` is set on 5th cumulative mute
  - Assert `end_reason = "disciplinary"` is set when Warning 3 expires without unmute
  - _Requirements: 4.1, 5.4, 5.5_

- [x] 4. Implement the dropout monitor





- [x] 4.1 Implement `run_dropout_monitor` coroutine


  - Subscribe to room connection quality / participant disconnect events
  - On loss event: set `silence_paused = True`, start 60s reconnection window
  - On reconnect within window: set `silence_paused = False`
  - On 60s timeout: set `end_reason = "candidate_leave"`, call `ctx.room.disconnect()`
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 4.2 Write unit tests for dropout monitor


  - Simulate disconnect event and assert timers pause
  - Assert termination fires with `end_reason = "candidate_leave"` after 60s without reconnect
  - Assert timers resume on reconnect within window
  - _Requirements: 6.1, 6.3, 6.4_

- [x] 5. Wire all tasks into start_mock_interview and add termination handoff





  - Register `@agent.on("user_speech_committed")` listener that updates `session_state["last_candidate_speech_time"]`
  - Create all three watchdog tasks with `asyncio.create_task` before `agent.say()` greeting
  - Wrap the interview body in `try/finally`: cancel all tasks, `await asyncio.gather(..., return_exceptions=True)`, call `_collect_transcript`, call `dispatch_session_complete`
  - Implement first-writer-wins guard: only set `end_reason` if it is currently empty string
  - Set `end_reason = "normal"` when the session completes without watchdog intervention
  - _Requirements: 1.1, 1.2, 1.4, 7.1, 7.2, 7.3, 7.4_

- [x] 5.2 Write integration test for concurrent termination race


  - Assert only the first `end_reason` is preserved when two watchdogs attempt to terminate simultaneously
  - _Requirements: 1.2_
