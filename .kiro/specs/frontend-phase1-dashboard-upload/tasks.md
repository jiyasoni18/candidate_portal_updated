# Implementation Plan

- [x] 1. Initialize Next.js project and configure Tailwind dark-mode theme





  - Scaffold a new Next.js 14+ App Router project inside a `frontend/` directory
  - Install dependencies: `tailwindcss`, `lucide-react`, and configure `tailwind.config.ts` with the `slate`/`zinc`/`emerald`/`indigo`/`amber` color palette
  - Set up `app/globals.css` with Tailwind base, components, and utilities directives
  - _Requirements: 1.2_

- [x] 2. Define shared TypeScript types and API client





- [x] 2.1 Create session type interfaces


  - Write `types/session.ts` with `JobSummary` and `SessionSummary` interfaces matching the backend `SessionSummary` response schema from `api/routers/practice.py`
  - _Requirements: 3.2_

- [x] 2.2 Implement typed API fetch wrappers


  - Write `lib/api.ts` with `fetchSessions()` and `initializeSession(formData)` functions using native `fetch`
  - Both functions must throw a typed error carrying HTTP status and backend error detail on non-2xx responses
  - _Requirements: 3.1, 5.1_

- [x] 3. Build root layout and sidebar navigation





- [x] 3.1 Implement root layout


  - Write `app/layout.tsx` as a Server Component applying `bg-slate-900 text-zinc-100 min-h-screen` to the root element
  - Import and render `<Sidebar />` alongside `{children}`
  - _Requirements: 1.2, 1.4_

- [x] 3.2 Implement Sidebar component

  - Write `components/Sidebar.tsx` as a `"use client"` component using `usePathname()` to highlight the active link
  - Render navigation links for "Practice Dashboard" (`/dashboard`), "Device Test Studio" (`/device-test`), and "Settings/Profile" (`/settings`) with `lucide-react` icons
  - _Requirements: 1.1, 1.3_

- [x] 4. Build StatusBadge and SessionGrid presentational components






- [x] 4.1 Implement StatusBadge component

  - Write `components/StatusBadge.tsx` mapping `completed`, `ready_to_start`, `parsing`, `scoring` status strings to their respective Tailwind pill classes including `animate-pulse` for in-progress states
  - Include a fallback style for unknown status values
  - _Requirements: 3.5, 3.6, 3.7_


- [x] 4.2 Implement SessionGrid component

  - Write `components/SessionGrid.tsx` accepting `sessions: SessionSummary[]` as a prop
  - Render columns: Target Role Title, Created Date (locale-formatted), Status (via `<StatusBadge />`), and Score (displaying `—` when `null`)
  - Render an empty-state message when `sessions.length === 0` instead of an empty table
  - _Requirements: 3.2, 3.3_

- [x] 4.3 Write unit tests for StatusBadge and SessionGrid


  - Test that `StatusBadge` renders correct CSS classes for each known status value
  - Test that `SessionGrid` with an empty array renders the empty-state message without throwing
  - Test that `SessionGrid` with mock data renders the correct number of rows
  - _Requirements: 3.2, 3.3, 3.5, 3.6, 3.7_

- [x] 5. Build the NewSessionModal upload form





- [x] 5.1 Implement modal shell and controlled open/close behavior


  - Write `components/NewSessionModal.tsx` as a `"use client"` component accepting `open: boolean` and `onClose: () => void` props
  - Use a `useEffect` watching `open` to reset all form state (jobTitle, jdText, file, errors) when the modal closes
  - _Requirements: 4.1, 5.5_

- [x] 5.2 Implement drag-and-drop file upload area

  - Add the file upload area inside the modal handling `onDragOver`, `onDragLeave`, and `onDrop` events as well as a standard file input click-to-browse path
  - On file selection via either path, validate the `.pdf` extension before storing in state; set a field error and reject the file if the extension is invalid
  - _Requirements: 4.4, 4.5_

- [x] 5.3 Implement client-side form validation

  - Add synchronous pre-submit validation that checks `jobTitle`, `jdText`, and `file` are all populated
  - Set per-field error messages and return early without firing a network request if any field is invalid
  - _Requirements: 4.2, 4.3_

- [x] 5.4 Implement form submission, loading state, and post-success navigation

  - On valid submit, build a `FormData` payload with keys `file` and `jd_text`, call `initializeSession()` from `lib/api.ts`
  - Set `submitting` state to `true` before the request and disable the submit button with a `lucide-react Loader2 animate-spin` spinner
  - On success, extract `session_id` from the response and call `router.push(`/practice/${session_id}`)` via `useRouter`
  - On error, set `submitError` state and re-enable the submit button
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [x] 5.5 Write unit tests for NewSessionModal validation


  - Test that submitting without a file shows the file field error and does not call `fetch`
  - Test that submitting without a job title shows the title field error
  - Test that the submit button is disabled and shows a spinner while `submitting` is `true`
  - _Requirements: 4.2, 4.3, 5.2_

- [x] 6. Build the Dashboard page and wire all components together





- [x] 6.1 Implement Dashboard page with data fetching


  - Write `app/dashboard/page.tsx` as a `"use client"` component with `sessions`, `loading`, `error`, and `modalOpen` state
  - On mount via `useEffect`, call `fetchSessions()` from `lib/api.ts`; populate `sessions` on success or set `error` on failure; set `loading` to `false` in both cases
  - _Requirements: 2.1, 3.1, 3.4_

- [x] 6.2 Render dashboard header, loading skeleton, and error state

  - Render the greeting banner ("Welcome back, Candidate") and the "+ New Practice Session" CTA button in the header block
  - Render a loading skeleton while `loading === true`
  - Render an error banner when `error` is set
  - Wire the CTA button to set `modalOpen` to `true`
  - _Requirements: 2.1, 2.2, 2.3, 3.4_

- [x] 6.3 Integrate SessionGrid and NewSessionModal into the Dashboard

  - Render `<SessionGrid sessions={sessions} />` once data is available
  - Render `<NewSessionModal open={modalOpen} onClose={() => setModalOpen(false)} />` controlled by `modalOpen` state
  - _Requirements: 2.3, 3.1, 3.2, 3.3_

- [x] 7. Add placeholder route for post-upload navigation target





  - Create `app/practice/[session_id]/page.tsx` as a minimal placeholder page so that `router.push(`/practice/${session_id}`)` resolves without a 404 after successful upload
  - _Requirements: 5.3_
