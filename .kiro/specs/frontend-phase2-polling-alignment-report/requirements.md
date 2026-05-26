# Requirements Document

## Introduction

Frontend Phase 2 implements the practice session waiting room and alignment report view at `app/practice/[session_id]/page.tsx`. After a candidate uploads their resume and job description, this page polls the FastAPI backend every 3 seconds to track background processing milestones. While the backend pipelines run, the page renders a status-specific loading canvas. Once the session reaches `ready_to_start`, the polling stops and the page transitions to a premium alignment report card displaying the resume-to-JD score, strengths, weaknesses, and a call-to-action button to enter the live interview booth. This phase replaces the Phase 1 placeholder route with a fully functional client component.

## Glossary

- **Practice Session Page**: The Next.js Client Component at `app/practice/[session_id]/page.tsx` that owns the polling loop and alignment report rendering.
- **Session ID**: The UUID route parameter extracted from the URL path, used as the identifier for all API calls on this page.
- **Polling Loop**: A `setInterval`-based mechanism that fires a `GET` request to the session detail endpoint every 3000ms to check for status changes.
- **Interval Ref**: A `useRef<ReturnType<typeof setInterval> | null>` that holds the active interval handle so it can be cleared on status change or component unmount.
- **Processing Status**: A session `status` value of `"parsing"` or `"scoring"` that indicates background LLM pipelines are still running.
- **Ready Status**: A session `status` value of `"ready_to_start"` that signals all background pipelines have completed and the alignment report is available.
- **Alignment Report**: The `resume_report` object returned in the session detail response, containing `score` (int 0–100), `reference_to_jd` (str), `strengths` (string array), and `weaknesses` (string array).
- **Score Tier**: A conditional color classification applied to the alignment score: High Alignment (≥75, emerald), Moderate Alignment (≥60, indigo/violet), Gaps Flagged (<60, amber/orange).
- **Session Detail Endpoint**: `GET http://localhost:8000/api/v1/practice/session/{session_id}` — the backend endpoint that returns the current session state including status and JSONB payload fields.
- **Interview Booth Route**: The Next.js route `/interview/{session_id}` that the candidate navigates to after reviewing the alignment report.
- **FastAPI Backend**: The local server running at `http://localhost:8000` that exposes the practice session API endpoints.
- **Client Component**: A Next.js component marked with `"use client"` that runs in the browser and may use React hooks and browser APIs.

---

## Requirements

### Requirement 1: Polling Engine Lifecycle

**User Story:** As a candidate, I want the page to automatically check my session status every few seconds so that I see the alignment report as soon as it is ready without manually refreshing.

#### Acceptance Criteria

1. WHEN the Practice Session Page mounts, THE Practice Session Page SHALL start a `setInterval` loop that fires every 3000 milliseconds, calling `GET /api/v1/practice/session/{session_id}`.
2. THE Practice Session Page SHALL store the interval handle in a `useRef` so that the same handle is accessible for cleanup without triggering re-renders.
3. WHEN the session status transitions to `"ready_to_start"`, THE Practice Session Page SHALL call `clearInterval` on the stored interval handle and SHALL NOT fire any further polling requests.
4. WHEN the Practice Session Page unmounts for any reason, THE Practice Session Page SHALL call `clearInterval` on the stored interval handle inside the `useEffect` cleanup function to prevent memory leaks and ghost network requests.
5. IF a polling request returns a non-2xx HTTP response, THEN THE Practice Session Page SHALL set an error state and SHALL stop the polling loop.
6. IF a polling request fails due to a network error, THEN THE Practice Session Page SHALL set an error state and SHALL stop the polling loop.

---

### Requirement 2: Processing State Loading Canvas

**User Story:** As a candidate, I want to see a descriptive loading screen while my resume is being processed so that I understand what the system is doing and do not think the page is broken.

#### Acceptance Criteria

1. WHILE the session status is `"parsing"`, THE Practice Session Page SHALL display the message "Aria is parsing your resume structural text layout..." in the loading canvas.
2. WHILE the session status is `"scoring"`, THE Practice Session Page SHALL display the message "Gemini is cross-referencing your background history against the target Job Description..." in the loading canvas.
3. THE Practice Session Page SHALL render the loading canvas using the `bg-slate-900` dark-mode theme with a centered column layout and an animated visual indicator (pulse or spinner).
4. WHILE the session is in a processing status, THE Practice Session Page SHALL NOT render any alignment report content.

---

### Requirement 3: Alignment Report — Score Display

**User Story:** As a candidate, I want to see my resume alignment score displayed prominently so that I can immediately understand how well my background matches the target role.

#### Acceptance Criteria

1. WHEN the session status is `"ready_to_start"`, THE Practice Session Page SHALL render the `resume_report.score` value as a large visual score element (circular badge or bold dial) showing the score out of 100.
2. WHEN `resume_report.score` is greater than or equal to 75, THE Practice Session Page SHALL apply emerald color styling to the score display element.
3. WHEN `resume_report.score` is greater than or equal to 60 and less than 75, THE Practice Session Page SHALL apply indigo or violet color styling to the score display element.
4. WHEN `resume_report.score` is less than 60, THE Practice Session Page SHALL apply amber or orange color styling to the score display element.
5. THE Practice Session Page SHALL render the `resume_report.reference_to_jd` narrative text beneath the score element as a supporting description.

---

### Requirement 4: Alignment Report — Strengths and Weaknesses

**User Story:** As a candidate, I want to see my identified strengths and preparation gaps so that I know what to highlight and what to work on before the interview.

#### Acceptance Criteria

1. WHEN the session status is `"ready_to_start"`, THE Practice Session Page SHALL render each item in `resume_report.strengths` as a list entry accompanied by a green checkmark icon.
2. WHEN the session status is `"ready_to_start"`, THE Practice Session Page SHALL render each item in `resume_report.weaknesses` as a list entry accompanied by an amber alert icon.
3. THE Practice Session Page SHALL render the strengths and weaknesses in separate, visually distinct card sections within a responsive flex layout.
4. IF `resume_report.strengths` is an empty array, THEN THE Practice Session Page SHALL render the strengths card section without throwing a runtime error.
5. IF `resume_report.weaknesses` is an empty array, THEN THE Practice Session Page SHALL render the weaknesses card section without throwing a runtime error.

---

### Requirement 5: Alignment Report — Interview Booth Navigation

**User Story:** As a candidate, I want a clear call-to-action button on the alignment report so that I can proceed to the live interview when I am ready.

#### Acceptance Criteria

1. WHEN the session status is `"ready_to_start"`, THE Practice Session Page SHALL render a prominent button labelled "Enter AI Practice Interview Booth".
2. WHEN a candidate clicks the "Enter AI Practice Interview Booth" button, THE Practice Session Page SHALL navigate to the route `/interview/{session_id}` using the Next.js router.
3. THE "Enter AI Practice Interview Booth" button SHALL be rendered below the strengths and weaknesses sections.

---

### Requirement 6: Error and Edge Case Handling

**User Story:** As a candidate, I want the page to handle errors and invalid session IDs gracefully so that I am never left on a broken or permanently loading screen.

#### Acceptance Criteria

1. IF the session detail API returns a 404 response, THEN THE Practice Session Page SHALL display an error message and render a navigation link back to the `/dashboard` route.
2. IF the polling loop encounters a network failure or non-2xx response, THEN THE Practice Session Page SHALL display an error message and render a navigation link back to the `/dashboard` route.
3. THE Practice Session Page SHALL NOT remain in an infinite loading state when an error condition is detected.
4. IF the session `status` is a value other than `"parsing"`, `"scoring"`, or `"ready_to_start"` (e.g., `"interviewing"`, `"completed"`), THEN THE Practice Session Page SHALL handle the status without throwing a runtime error, rendering an appropriate fallback message.

---

### Requirement 7: API Client Extension

**User Story:** As a frontend developer, I want a typed API fetch wrapper for the session detail endpoint so that the polling component can retrieve session data with consistent error handling.

#### Acceptance Criteria

1. THE `lib/api.ts` module SHALL export a `fetchSession(sessionId: string)` function that sends a `GET` request to `http://localhost:8000/api/v1/practice/session/{sessionId}`.
2. THE `fetchSession` function SHALL return a typed `SessionDetail` object on a 2xx response.
3. IF the `fetchSession` request returns a non-2xx response, THEN THE `fetchSession` function SHALL throw an `ApiError` carrying the HTTP status and backend error detail, consistent with the existing `ApiError` pattern in `lib/api.ts`.
4. THE `types/session.ts` module SHALL define a `SessionDetail` interface containing at minimum: `session_id` (string), `status` (string), `job` (JobSummary), `resume_report` (ResumeReport or null), and `created_at` (string).
5. THE `types/session.ts` module SHALL define a `ResumeReport` interface with fields: `score` (number), `reference_to_jd` (string), `strengths` (string array), and `weaknesses` (string array).
