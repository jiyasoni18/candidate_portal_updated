# Frontend Phase 3: LiveKit WebRTC Voice Studio & Performance Assessment Card Views

## 1. Objective
Build the real-time voice interview page and post-interview scorecard view. This phase handles microphone verification, manages LiveKit connection tokens, listens to incoming real-time guardrail notification data streams, and exposes the final performance evaluation graphs once a session is completed.

## 2. Technical Stack & Dependencies
- **Framework Primitive**: Next.js Client Component (`"use client"`).
- **WebRTC Connection Core**: `livekit-client` and `@livekit/components-react`.
- **Style Overlays**: Tailwind CSS combined with `lucide-react` status badges.

---

## 3. UI Component Architecture & Logic Specs

### 3.1. Pre-Join Device Check & Verification Layer (`components/MediaPreCheck.tsx`)
Before accessing the live room canvas, candidates must verify their local media settings using native browser controls:
- **Device Enumeration**: Use `navigator.mediaDevices.enumerateDevices()` to load available audio inputs (`audioinput`) into state selection options.
- **Microphone Signal Bar Test**: Instantiate an `AudioContext` and create an analyser node mapped to the local media track stream. Track frequency spectrum volumes; if average mic signal volumes register above threshold limits, transition status indicators to green ("Microphone verified").
- **Permission Check Action**: Clicking **"Enter Practice Booth"** triggers a `POST` request to `/api/v1/practice/session/${id}/start` to fetch the session tokens.

### 3.2. Live WebRTC Studio View Container (`app/interview/[session_id]/page.tsx`)
Once the authorization payload initializes, mount the structural `<LiveKitRoom />` wrapper component:
- **Props Handlers**: Pass the backend-issued `livekit_token` and `livekit_url` explicitly into connection attributes. Inject `audio=true` and `video=true` defaults.
- **Sub-Component Controls UI**:
  - Mount `<RoomAudioRenderer />` to route real-time AI audio streams through browser hardware.
  - Render local camera inputs natively inside a clean participant panel block using the `useTracks` state hook filter.
  - Include an explicit, large **"End Practice Session"** button triggering explicit disconnect hooks (`room.disconnect()`).

### 3.3. LiveKit Data Channel Guardrail Subscriptions
Create an inner context listener (`RoomNotificationHandler`) subscribing directly to `RoomEvent.DataReceived` events:
- **Watchdog Signal Intercept**: Listen for serialized JSON messages sent by the backend watchdog worker.
- **Interactive Action Mapping**:
  - If a message matches `type: "session_ended"` and `reason: "silence_timeout"`, instantly disconnect the audio track and update local state arrays to display an alert banner: *"The practice room closed due to prolonged silence."*
  - If a message matches `type: "session_ended"` and `reason: "disciplinary"`, render the warning block: *"Session terminated due to camera-off policy enforcement."*
- **Session Closer Transition**: When a session ends normally or via watchdogs, push the client router view forward to path: `/practice/${session_id}/assessment`.

### 3.4. Post-Interview Performance Assessment Card (`app/practice/[session_id]/assessment/page.tsx`)
Renders the complete evaluation dashboard view using the strict backend payload data arrays from Phase 10:
- **Verdict Display Header**: Render a prominent text card displaying the calculated evaluation metric string (`practice_verdict`, e.g., "Strong Alignment").
- **Completion Factor Callout**: Show an explicit comparison bar demonstrating the session's overall `completion_ratio` and total `turns_analyzed` count.
- **Dimension Score Breakdown Card**: Map out categorized section badges dynamically (`dimension_scores.technical`, `dimension_scores.communication`), rendering individual quantitative score values, qualitative verdicts, and transcript evidence context quotes.
- **Technical Round Probes Bullet Grid**: Render a distinct highlights container block at the bottom displaying your custom `technical_round_probes` array items to guide their future interview preparation focus.

---

## 4. Verification Check Constraints
The Kiro agent must verify successful completion by asserting media states:
1. Ensure that if a candidate blocks browser microphone permissions during the pre-check flow, the workspace catches the failure gracefully, locks the join button, and renders a supportive text notification troubleshooting step instead of hard-crashing the page template.
2. Confirm that unmounting or navigating away from the active interview component handles track teardown routines perfectly by clearing browser media access indicator lights instantly.