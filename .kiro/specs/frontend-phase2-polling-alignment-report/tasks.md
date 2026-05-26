# Implementation Plan

- [x] 1. Extend types and API client





- [x] 1.1 Add `ResumeReport` and `SessionDetail` interfaces to `types/session.ts`


  - Add `ResumeReport` interface with `score` (number), `reference_to_jd` (string), `strengths` (string[]), `weaknesses` (string[])
  - Add `SessionDetail` interface with `session_id`, `status`, `created_at`, `job` (JobSummary), `resume_report` (ResumeReport | null), `resume_score` (number | null)
  - _Requirements: 7.4, 7.5_

- [x] 1.2 Add `fetchSession` function to `lib/api.ts`


  - Implement `fetchSession(sessionId: string): Promise<SessionDetail>` using the existing `handleResponse` pattern
  - _Requirements: 7.1, 7.2, 7.3_

- [x] 2. Implement the Practice Session Page





- [x] 2.1 Replace the placeholder with the full client component shell


  - Mark the file `"use client"`, add `useState` for `status`, `resumeReport`, and `error`, add `useRef` for the interval handle
  - Extract `session_id` from `params` and pass it to the polling hook
  - _Requirements: 1.1, 1.2_

- [x] 2.2 Implement the polling `useEffect`

  - Define the `poll` async function that calls `fetchSession`, updates `status`, and on `ready_to_start` calls `clearInterval` and sets `resumeReport`
  - Call `poll()` immediately on mount, then start `setInterval(poll, 3000)` and store the handle in `intervalRef`
  - Return a cleanup function that calls `clearInterval(intervalRef.current)` to handle unmount
  - On any caught error, call `clearInterval` and set `error` state
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

- [x] 2.3 Implement `ProcessingCanvas` inline sub-component

  - Accept `status: string | null` prop and map `"parsing"` and `"scoring"` to their specified message strings, with a generic fallback
  - Render centered dark-mode layout with animated pulse indicator and status message
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 2.4 Implement `ScoreMeter` inline sub-component

  - Accept `score: number` and `referenceToJd: string` props
  - Apply emerald/indigo/amber color classes based on the ≥75 / ≥60 / <60 thresholds
  - Render score tier label ("High Alignment", "Moderate Alignment", "Gaps Flagged") alongside the circular badge
  - Render `referenceToJd` as a supporting paragraph below the badge
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 2.5 Implement `StrengthsCard` and `WeaknessesCard` inline sub-components

  - `StrengthsCard`: accept `items: string[]`, render each with a `lucide-react CheckCircle2` icon in `text-emerald-400`
  - `WeaknessesCard`: accept `items: string[]`, render each with a `lucide-react AlertTriangle` icon in `text-amber-400`
  - Both cards use `bg-slate-800/50 border border-slate-700 rounded-xl p-6` styling; render without error when `items` is empty
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 2.6 Implement `AlignmentReport` inline sub-component and interview booth CTA

  - Compose `ScoreMeter`, `StrengthsCard`, `WeaknessesCard` in a responsive layout
  - Render the "Enter AI Practice Interview Booth" button below the cards
  - Wire the button to `router.push(`/interview/${sessionId}`)` via `useRouter`
  - _Requirements: 5.1, 5.2, 5.3_

- [x] 2.7 Implement `ErrorState` inline sub-component

  - Render the error message in `text-red-400` and a `<Link href="/dashboard">` back to the dashboard
  - _Requirements: 6.1, 6.2, 6.3_

- [x] 2.8 Wire render logic in the page component

  - If `error` is set → render `ErrorState`
  - Else if `status === 'ready_to_start'` and `resumeReport` is non-null → render `AlignmentReport`
  - Else → render `ProcessingCanvas`
  - Handle unknown status values in `ProcessingCanvas` fallback without throwing
  - _Requirements: 2.4, 6.4_

- [x] 3. Write unit tests for the Practice Session Page





  - Test `ProcessingCanvas` renders the correct message for `"parsing"` and `"scoring"` status values
  - Test `ScoreMeter` applies emerald classes for score ≥75, indigo for ≥60, amber for <60
  - Test `StrengthsCard` and `WeaknessesCard` render correct item counts and do not throw on empty arrays
  - Test `ErrorState` renders when `fetchSession` throws an `ApiError`
  - Test `clearInterval` is called when status reaches `"ready_to_start"` and on component unmount
  - _Requirements: 1.3, 1.4, 2.1, 2.2, 3.2, 3.3, 3.4, 4.4, 4.5, 6.1_
