# Requirements Document

## Introduction

This document defines the requirements for Frontend Phase 1 of the Candidate Practice Portal. The scope covers three interconnected UI deliverables built in Next.js (App Router): the master layout with persistent sidebar navigation, the candidate dashboard with a historical session grid, and the multi-part asset upload modal that initiates a new practice session by submitting a resume PDF and job description text to the FastAPI backend.

## Glossary

- **Candidate Portal**: The Next.js web application used by candidates to manage and conduct AI-powered practice interviews.
- **Dashboard**: The primary page (`/dashboard`) that lists all historical practice sessions for the candidate.
- **Session Grid**: The tabular card list on the Dashboard that renders one row per historical practice session.
- **Session**: A single practice interview record, identified by a unique `session_id`, containing a target role title, creation timestamp, processing status, and optional performance score.
- **New Session Modal**: A controlled overlay form component (`NewSessionModal`) that collects a job title, job description text, and a resume PDF file, then submits them to the backend to create a new Session.
- **Status Badge**: A styled pill element that visually communicates the current processing state of a Session (`completed`, `ready_to_start`, `parsing`, `scoring`).
- **FastAPI Backend**: The local server running at `http://localhost:8000` that exposes the practice session API endpoints.
- **App Router**: The Next.js 14+ file-system routing mechanism using the `app/` directory.
- **Client Component**: A Next.js component marked with `"use client"` that runs in the browser and may use React hooks and browser APIs.
- **FormData**: The native browser API used to construct multipart/form-data payloads for file upload requests.

---

## Requirements

### Requirement 1: Master Layout and Sidebar Navigation

**User Story:** As a candidate, I want a persistent sidebar navigation structure so that I can move between portal sections without losing my current page context.

#### Acceptance Criteria

1. THE Candidate Portal SHALL render a fixed sidebar on every page containing navigation links to "Practice Dashboard", "Device Test Studio", and "Settings/Profile".
2. THE Candidate Portal SHALL apply a dark-mode base theme using `bg-slate-900` and `text-zinc-100` CSS classes to the root layout so that all child pages inherit the premium dark aesthetic.
3. WHEN a candidate navigates to any route within the portal, THE Candidate Portal SHALL display the sidebar without re-mounting or flickering.
4. THE Candidate Portal SHALL define the root layout in `app/layout.tsx` as a Server Component that wraps all page content with the sidebar structure.

---

### Requirement 2: Dashboard Header and Call-to-Action

**User Story:** As a candidate, I want a welcoming dashboard header with a clear action button so that I can quickly start a new practice session.

#### Acceptance Criteria

1. THE Dashboard SHALL render a greeting banner displaying the text "Welcome back, Candidate" on page load.
2. THE Dashboard SHALL render a primary call-to-action button labelled "+ New Practice Session" in the header block.
3. WHEN a candidate clicks the "+ New Practice Session" button, THE Dashboard SHALL open the New Session Modal.

---

### Requirement 3: Session History Grid

**User Story:** As a candidate, I want to see all my past practice sessions in a structured grid so that I can review my history and track progress.

#### Acceptance Criteria

1. WHEN the Dashboard mounts, THE Dashboard SHALL send a `GET` request to `http://localhost:8000/api/v1/practice/sessions` to retrieve the candidate's session list.
2. THE Session Grid SHALL render one row per session returned by the API, displaying the columns: Target Role Title, Created Date, Status Badge, and Performance Score.
3. IF the API returns an empty session list, THEN THE Session Grid SHALL render an empty-state message instead of throwing a runtime error or blank screen.
4. IF the API request fails, THEN THE Dashboard SHALL display an error state message to the candidate without crashing the page.
5. WHILE a session has a status value of `completed`, THE Status Badge SHALL render with the CSS classes `bg-emerald-500/10 text-emerald-400 border border-emerald-500/20`.
6. WHILE a session has a status value of `ready_to_start`, THE Status Badge SHALL render with the CSS classes `bg-indigo-500/10 text-indigo-400 border border-indigo-500/20`.
7. WHILE a session has a status value of `parsing` or `scoring`, THE Status Badge SHALL render with the CSS classes `bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse`.

---

### Requirement 4: New Session Modal Form Fields

**User Story:** As a candidate, I want a structured upload form so that I can provide my resume and target job details to initialize a new practice session.

#### Acceptance Criteria

1. THE New Session Modal SHALL contain a text input field for the job title, a multiline textarea field mapped to `jd_text`, and a file upload area restricted to `.pdf` files only.
2. WHEN a candidate attempts to submit the New Session Modal form without selecting a PDF file, THE New Session Modal SHALL display a client-side validation error message and SHALL NOT send a network request to the backend.
3. WHEN a candidate attempts to submit the New Session Modal form without entering a job title, THE New Session Modal SHALL display a client-side validation error message and SHALL NOT send a network request to the backend.
4. THE New Session Modal file upload area SHALL accept files via both drag-and-drop interaction and standard file browser selection.
5. WHEN a candidate selects a file that does not have a `.pdf` extension, THE New Session Modal SHALL display a validation error and SHALL NOT store the invalid file in component state.

---

### Requirement 5: New Session Form Submission and Navigation

**User Story:** As a candidate, I want the upload form to submit my assets and redirect me to the new session page so that I can begin my practice session without manual navigation.

#### Acceptance Criteria

1. WHEN a candidate submits the New Session Modal with valid inputs, THE New Session Modal SHALL assemble a `FormData` payload containing the PDF file under the key `file` and the job description text under the key `jd_text`, then send a `POST` request to `http://localhost:8000/api/v1/practice/initialize`.
2. WHILE a form submission request is in-flight, THE New Session Modal SHALL disable the submit button and render a loading spinner to prevent duplicate submissions.
3. WHEN the backend returns a successful response containing a `session_id`, THE New Session Modal SHALL navigate the candidate to the route `/practice/{session_id}` using the Next.js router.
4. IF the backend returns an error response, THEN THE New Session Modal SHALL display an error message to the candidate and SHALL re-enable the submit button.
5. WHEN a candidate closes the New Session Modal without submitting, THE New Session Modal SHALL reset all form field values to their default empty state.
