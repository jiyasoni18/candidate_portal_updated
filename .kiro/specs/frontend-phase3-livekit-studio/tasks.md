# Implementation Plan — Frontend Phase 3: LiveKit WebRTC Voice Studio & Assessment Scorecard

- [x] 1. Install LiveKit dependencies and extend TypeScript types





  - Run `npm install livekit-client @livekit/components-react` inside the `frontend/` directory
  - Append `StartSessionResponse`, `DimensionScore`, and `InterviewAssessment` interfaces to `frontend/types/session.ts`
  - Extend the existing `SessionDetail` interface with `interview_assessment: InterviewAssessment | null`
  - Add `startSession(sessionId: string): Promise<StartSessionResponse>` to `frontend/lib/api.ts`
  - _Requirements: 2.1, 4.1_

- [x] 2. Implement `MediaPreCheck` component





- [x] 2.1 Build device enumeration and AudioContext signal sampling


  - Create `frontend/components/MediaPreCheck.tsx` as a `"use client"` component
  - Call `navigator.mediaDevices.enumerateDevices()` on mount and populate `audioinput` device dropdown
  - On device selection, call `getUserMedia`, create `AudioContext` + `AnalyserNode`, start 100ms `setInterval` sampling `getByteFrequencyData` average amplitude
  - Set `micStatus = "verified"` when average amplitude exceeds 10
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 2.2 Handle permission errors and teardown

  - Catch `NotAllowedError` and `NotFoundError` from `getUserMedia`, set `micStatus = "error"` with descriptive message, disable the join button
  - In `useEffect` cleanup: stop all `MediaStreamTrack` instances, close `AudioContext`, clear sampling interval
  - _Requirements: 1.4, 1.5_

- [x] 2.3 Wire "Enter Practice Booth" button to `startSession` API call

  - On button click (only when `micStatus === "verified"`), call `startSession(sessionId)` and invoke `onReady(token, url)` prop with the response values
  - Show inline loading state during the POST request; show inline error message on failure without navigating
  - _Requirements: 1.6_

- [x] 2.4 Write unit tests for MediaPreCheck


  - Mock `navigator.mediaDevices.getUserMedia` and `enumerateDevices` in `frontend/__tests__/MediaPreCheck.test.tsx`
  - Assert permission error state disables the button and shows error text
  - Assert verified state enables the button and calls `startSession` on click
  - _Requirements: 1.3, 1.4, 1.6_

- [x] 3. Implement the Live WebRTC Studio Page





- [x] 3.1 Build the Studio Page shell with MediaPreCheck gate


  - Create `frontend/app/interview/[session_id]/page.tsx` as a `"use client"` component
  - Render `<MediaPreCheck sessionId onReady={...} />` when `livekitToken` state is null
  - On `onReady` callback, set `livekitToken` and `livekitUrl` state to transition to the room view
  - _Requirements: 2.1_


- [x] 3.2 Mount LiveKitRoom with audio renderer and local camera panel





  - Render `<LiveKitRoom token={livekitToken} serverUrl={livekitUrl} audio={true} video={true}>` once token is available
  - Mount `<RoomAudioRenderer />` inside the room for remote AI audio routing
  - Implement `LocalCameraPanel` inline using `useTracks([{ source: Track.Source.Camera, withPlaceholder: true }], { onlySubscribed: false })` and render the first local track via `<VideoTrack />`
  - _Requirements: 2.1, 2.2, 2.3_


- [x] 3.3 Add End Session button and connection error handling




  - Implement `EndSessionButton` inline using `useRoomContext()` to access `room.disconnect()`; on click, call disconnect and navigate to `/practice/{session_id}/assessment`
  - Add an `onError` handler on `<LiveKitRoom>` that sets an `alertMessage` state; render an error banner with the reason and a `/dashboard` link when set
  - _Requirements: 2.4, 2.5_

- [x] 4. Implement `RoomNotificationHandler`





  - Create `RoomNotificationHandler` as an inline component inside the Studio Page file
  - Use `useRoomContext()` and `useRouter()`; in `useEffect`, register `room.on(RoomEvent.DataReceived, handler)` and `room.on(RoomEvent.Disconnected, () => router.push(...))`
  - In the DataReceived handler: decode `Uint8Array` via `TextDecoder`, attempt `JSON.parse` (silently discard on failure), match `type === "session_ended"` and set alert message based on `reason` field, then call `room.disconnect()`
  - Return cleanup function calling `room.off(...)` for both events
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 4.1 Write unit tests for Studio Page and RoomNotificationHandler


  - Mock `@livekit/components-react` hooks at module level in `frontend/__tests__/InterviewStudioPage.test.tsx`
  - Assert `MediaPreCheck` renders before token is set; assert `LiveKitRoom` renders after token is set
  - Assert DataReceived handler sets correct alert message for each watchdog reason
  - _Requirements: 3.2, 3.3_

- [x] 5. Implement the Post-Interview Assessment Page





- [x] 5.1 Build the Assessment Page with polling logic


  - Create `frontend/app/practice/[session_id]/assessment/page.tsx` as a `"use client"` component
  - Implement `setInterval` polling at 3000ms calling `fetchSession(sessionId)`, clearing the interval when `status === "completed"` or on fetch error
  - Clear the interval in `useEffect` cleanup on unmount
  - Render a loading spinner while polling; render an error state with `/dashboard` link on failure
  - _Requirements: 4.1, 4.6, 4.7, 4.8_

- [x] 5.2 Render VerdictHeader and CompletionCallout

  - Implement `VerdictHeader` inline: render `practice_verdict` and `overall_score` in a centered circle badge, color-coded (≥80 emerald, ≥68 indigo, ≥52 amber, <52 red)
  - Implement `CompletionCallout` inline: render `(completion_ratio * 100).toFixed(0)%` with a Tailwind progress bar and `turns_analyzed` count
  - _Requirements: 4.2, 4.3_

- [x] 5.3 Render DimensionGrid and TechnicalProbesGrid

  - Implement `DimensionCard` inline: render `label`, `score/100`, `verdict` badge, `evidence` quote block, and `gaps` bullet list
  - Implement `DimensionGrid` inline: map `Object.entries(dimension_scores)` to `DimensionCard` in a 2-column responsive grid
  - Implement `TechnicalProbesGrid` inline: render `technical_round_probes` as a 3-column grid of numbered probe cards
  - Handle the edge case where `interview_assessment` is null on a `completed` session by showing "Assessment is still processing..." text
  - _Requirements: 4.4, 4.5_

- [x] 5.4 Write unit tests for Assessment Page


  - Mock `fetchSession` in `frontend/__tests__/AssessmentPage.test.tsx` returning a completed session with a full `InterviewAssessment` fixture
  - Assert `practice_verdict`, `overall_score`, all 4 dimension labels, and all 3 probe strings render
  - Assert polling interval is cleared on component unmount
  - _Requirements: 4.2, 4.3, 4.4, 4.5, 4.8_
