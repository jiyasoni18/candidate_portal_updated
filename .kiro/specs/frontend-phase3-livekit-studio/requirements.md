# Requirements Document

## Introduction

Frontend Phase 3 builds the real-time voice interview workspace and post-interview performance assessment view for the Candidate Portal. It covers three distinct UI surfaces: a pre-join media verification component (`MediaPreCheck`), a live WebRTC studio page powered by `@livekit/components-react`, and a post-interview scorecard page that renders the completion-weighted grading output from the backend Phase 10 pipeline. The phase also introduces a data channel listener (`RoomNotificationHandler`) that intercepts backend watchdog signals and drives session teardown transitions.

## Glossary

- **MediaPreCheck**: A React client component that verifies microphone permissions and audio signal levels before a candidate enters the live interview room.
- **AudioContext**: The Web Audio API interface used to create an analyser node for real-time microphone signal level measurement.
- **AnalyserNode**: A Web Audio API node that provides real-time frequency and time-domain analysis of an audio stream.
- **LiveKitRoom**: The `@livekit/components-react` wrapper component that manages a WebRTC room connection lifecycle.
- **RoomAudioRenderer**: A `@livekit/components-react` component that routes remote audio tracks through the browser's audio hardware.
- **RoomNotificationHandler**: An inner React component that subscribes to LiveKit `RoomEvent.DataReceived` events and processes JSON watchdog signals from the backend.
- **WatchdogSignal**: A JSON message sent over the LiveKit data channel by the backend Phase 8 watchdog worker, containing `type` and `reason` fields.
- **InterviewAssessmentSchema**: The backend Pydantic model serialized to JSONB in `practice_sessions.interview_assessment`, containing `overall_score`, `practice_verdict`, `dimension_scores`, `technical_round_probes`, `completion_ratio`, and `turns_analyzed`.
- **DimensionScoreCard**: A sub-object within `InterviewAssessmentSchema` containing `score`, `label`, `verdict`, `evidence`, `strengths`, and `gaps` for one evaluation dimension.
- **completion_ratio**: A float (0.0–1.0) representing the fraction of expected interview questions answered by the candidate, used as a weighting multiplier in the final score formula.
- **practice_verdict**: A string label derived from the final score threshold mapping (e.g., "High Alignment", "Strong Alignment").
- **technical_round_probes**: An array of exactly 3 strings representing deep-dive engineering topics drawn from the candidate's transcript, used for future preparation guidance.
- **livekit_token**: A signed JWT returned by `POST /api/v1/practice/session/{session_id}/start` granting the candidate access to the LiveKit room.
- **livekit_url**: The WebSocket URL of the LiveKit server, returned alongside `livekit_token`.
- **session_id**: A UUID string uniquely identifying a practice session, used as a URL path parameter across all Phase 3 routes.
- **Studio Page**: The Next.js page at `app/interview/[session_id]/page.tsx` that hosts the live WebRTC interview room.
- **Assessment Page**: The Next.js page at `app/practice/[session_id]/assessment/page.tsx` that renders the post-interview scorecard.

---

## Requirements

### Requirement 1 — Media Pre-Check Component

**User Story:** As a candidate, I want to verify my microphone is working before entering the interview room, so that I can confirm my audio setup is functional and avoid technical issues during the session.

#### Acceptance Criteria

1. WHEN the MediaPreCheck component mounts, THE MediaPreCheck SHALL call `navigator.mediaDevices.enumerateDevices()` and populate a dropdown with all available `audioinput` device labels.
2. WHEN the candidate selects an audio input device, THE MediaPreCheck SHALL instantiate an `AudioContext`, connect an `AnalyserNode` to the selected device's `MediaStream`, and sample average frequency amplitude values at a minimum interval of 100 milliseconds.
3. WHEN the sampled average amplitude exceeds a threshold of 10 on a 0–255 scale, THE MediaPreCheck SHALL update the microphone status indicator to a green "Microphone verified" state.
4. IF `navigator.mediaDevices.getUserMedia` rejects with a `NotAllowedError` or `NotFoundError`, THEN THE MediaPreCheck SHALL display a descriptive troubleshooting message and disable the "Enter Practice Booth" button.
5. WHEN the MediaPreCheck component unmounts, THE MediaPreCheck SHALL stop all active `MediaStreamTrack` instances and close the `AudioContext` to release browser media access indicators.
6. WHEN the candidate clicks "Enter Practice Booth" and microphone status is verified, THE MediaPreCheck SHALL issue a `POST` request to `/api/v1/practice/session/{session_id}/start` and pass the returned `livekit_token` and `livekit_url` to the parent Studio Page.

---

### Requirement 2 — Live WebRTC Studio Page

**User Story:** As a candidate, I want a live interview room that connects me to the AI voice agent, so that I can conduct my practice session with real-time audio and video.

#### Acceptance Criteria

1. WHEN the Studio Page receives a valid `livekit_token` and `livekit_url`, THE Studio Page SHALL render a `<LiveKitRoom>` component with `audio={true}` and `video={true}` props and the provided token and server URL.
2. WHILE the LiveKit room connection is active, THE Studio Page SHALL render a `<RoomAudioRenderer>` component to route remote AI audio tracks through the browser's audio hardware.
3. WHILE the LiveKit room connection is active, THE Studio Page SHALL render the candidate's local camera track using the `useTracks` hook filtered to `Track.Source.Camera` for the local participant.
4. WHEN the candidate clicks the "End Practice Session" button, THE Studio Page SHALL call `room.disconnect()` and navigate the client router to `/practice/{session_id}/assessment`.
5. IF the LiveKit room connection fails with a connection error, THEN THE Studio Page SHALL display an error banner with the failure reason and a link back to `/dashboard`.

---

### Requirement 3 — Room Notification Handler

**User Story:** As a candidate, I want the interview room to respond automatically to backend watchdog signals, so that I am informed when my session ends due to silence or policy enforcement.

#### Acceptance Criteria

1. WHILE the LiveKit room connection is active, THE RoomNotificationHandler SHALL subscribe to `RoomEvent.DataReceived` events and attempt to parse each received payload as a UTF-8 JSON string.
2. WHEN a received data message contains `type: "session_ended"` and `reason: "silence_timeout"`, THE RoomNotificationHandler SHALL display the alert banner "The practice room closed due to prolonged silence." and disconnect the room.
3. WHEN a received data message contains `type: "session_ended"` and `reason: "disciplinary"`, THE RoomNotificationHandler SHALL display the alert banner "Session terminated due to camera-off policy enforcement." and disconnect the room.
4. WHEN the room disconnects for any reason (normal end, watchdog signal, or network drop), THE RoomNotificationHandler SHALL navigate the client router to `/practice/{session_id}/assessment`.
5. IF a received data message cannot be parsed as valid JSON, THEN THE RoomNotificationHandler SHALL silently discard the message without throwing an unhandled exception.

---

### Requirement 4 — Post-Interview Assessment Page

**User Story:** As a candidate, I want to see a detailed scorecard after my interview, so that I can understand my performance and identify areas for improvement.

#### Acceptance Criteria

1. WHEN the Assessment Page mounts, THE Assessment Page SHALL fetch the session data from `GET /api/v1/practice/session/{session_id}` and render a loading state until the response resolves.
2. WHEN the fetched session has `status: "completed"` and a non-null `interview_assessment` field, THE Assessment Page SHALL render the `practice_verdict` string and `overall_score` integer in a prominent header card.
3. WHEN the fetched session has `status: "completed"`, THE Assessment Page SHALL render a completion callout displaying the `completion_ratio` as a percentage and the `turns_analyzed` integer count.
4. WHEN the fetched session has `status: "completed"`, THE Assessment Page SHALL render one scorecard card per entry in `dimension_scores`, displaying the dimension `label`, `score`, `verdict`, `evidence`, and `gaps` array items.
5. WHEN the fetched session has `status: "completed"`, THE Assessment Page SHALL render the `technical_round_probes` array as a distinct preparation grid with one item per probe string.
6. IF the fetched session has `status` other than `"completed"`, THEN THE Assessment Page SHALL poll `GET /api/v1/practice/session/{session_id}` at a 3-second interval until the status transitions to `"completed"`, then stop polling and render the scorecard.
7. IF the fetch request fails with a network or HTTP error, THEN THE Assessment Page SHALL display an error message and a navigation link back to `/dashboard`.
8. WHEN the Assessment Page unmounts, THE Assessment Page SHALL clear all active polling intervals to prevent memory leaks.
