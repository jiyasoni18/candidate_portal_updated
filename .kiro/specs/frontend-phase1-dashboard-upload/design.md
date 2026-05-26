# Design Document: Frontend Phase 1 — Dashboard, Session Grid & Upload Modal

## Overview

This document describes the architecture and component design for the first phase of the Next.js Candidate Portal UI. The deliverables are:

1. A root `app/layout.tsx` with a persistent dark-mode sidebar.
2. A `app/dashboard/page.tsx` that fetches and renders the historical session grid.
3. A `components/NewSessionModal.tsx` controlled modal that handles multi-part asset upload and post-success navigation.

The frontend communicates directly with the FastAPI backend running at `http://localhost:8000`. No authentication layer is introduced in this phase — the backend uses a hardcoded default user ID.

---

## Architecture

```mermaid
graph TD
    A[app/layout.tsx\nServer Component] --> B[components/Sidebar.tsx\nClient Component]
    A --> C[app/dashboard/page.tsx\nClient Component]

    C -->|useEffect GET| D[FastAPI\nGET /api/v1/practice/sessions]
    C -->|opens modal| E[components/NewSessionModal.tsx\nClient Component]

    E -->|POST FormData| F[FastAPI\nPOST /api/v1/practice/initialize]
    F -->|returns session_id| G[Next.js router.push\n/practice/session_id]

    D -->|SessionSummary[]| C
    C --> H[components/StatusBadge.tsx\nPure Component]
    C --> I[components/SessionGrid.tsx\nPure Component]
```

### Key Design Decisions

- The root layout is a Server Component. Only components that require browser APIs or React state are marked `"use client"`.
- All API calls use native `fetch` — no third-party HTTP client is introduced.
- The modal is a controlled component: open/close state lives in the Dashboard page, not inside the modal itself, keeping the modal stateless about its own visibility.
- Form state (job title, jd_text, file) is managed with `useState` hooks inside the modal. On close, state is explicitly reset.
- The `StatusBadge` is extracted as a pure presentational component to keep the grid clean and the badge logic testable in isolation.

---

## Project Structure

```
frontend/
├── app/
│   ├── layout.tsx                  # Root layout — Server Component
│   ├── globals.css                 # Tailwind base imports
│   ├── dashboard/
│   │   └── page.tsx                # Dashboard page — Client Component
│   └── practice/
│       └── [session_id]/
│           └── page.tsx            # Placeholder route (Phase 2 target)
├── components/
│   ├── Sidebar.tsx                 # Persistent nav — Client Component
│   ├── NewSessionModal.tsx         # Upload modal — Client Component
│   ├── SessionGrid.tsx             # Session list table — pure component
│   └── StatusBadge.tsx             # Status pill — pure component
├── lib/
│   └── api.ts                      # Typed fetch wrappers for backend calls
├── types/
│   └── session.ts                  # TypeScript interfaces matching backend schemas
├── tailwind.config.ts
├── next.config.ts
└── package.json
```

---

## Components and Interfaces

### `app/layout.tsx` (Server Component)

Wraps all pages with the dark-mode base theme and renders the `Sidebar`. Does not use any browser APIs so it remains a Server Component, improving initial page load.

```tsx
// Applies: bg-slate-900 text-zinc-100 min-h-screen
// Renders: <Sidebar /> + {children}
```

---

### `components/Sidebar.tsx` (`"use client"`)

Persistent left-rail navigation. Uses `usePathname()` from `next/navigation` to highlight the active link.

Navigation items:
| Label | Route |
|---|---|
| Practice Dashboard | `/dashboard` |
| Device Test Studio | `/device-test` |
| Settings / Profile | `/settings` |

Uses `lucide-react` icons (`LayoutDashboard`, `Mic`, `Settings`) alongside each label.

---

### `app/dashboard/page.tsx` (`"use client"`)

The primary page component. Owns the modal open/close state and the session list data state.

State shape:
```typescript
const [sessions, setSessions] = useState<SessionSummary[]>([]);
const [loading, setLoading] = useState(true);
const [error, setError] = useState<string | null>(null);
const [modalOpen, setModalOpen] = useState(false);
```

On mount (`useEffect`), calls `GET /api/v1/practice/sessions`. On success, populates `sessions`. On failure, sets `error`. Sets `loading` to `false` in both cases.

Renders:
- Header block: greeting text + "+ New Practice Session" button.
- Loading skeleton while `loading === true`.
- Error banner if `error` is set.
- `<SessionGrid sessions={sessions} />` once data is available.
- `<NewSessionModal open={modalOpen} onClose={() => setModalOpen(false)} />`.

---

### `components/SessionGrid.tsx` (pure component)

Receives `sessions: SessionSummary[]` as a prop. Renders a styled table/card list.

Props:
```typescript
interface SessionGridProps {
  sessions: SessionSummary[];
}
```

Columns rendered per row:
| Column | Source field | Notes |
|---|---|---|
| Target Role | `session.job.title` | Plain text |
| Created | `session.created_at` | Formatted as locale date string |
| Status | `session.status` | Rendered via `<StatusBadge status={...} />` |
| Score | `session.resume_score` | Displays `—` when `null` |

Empty state: when `sessions.length === 0`, renders a centered message ("No practice sessions yet. Start your first one above.") instead of an empty table.

---

### `components/StatusBadge.tsx` (pure component)

Maps a status string to a styled pill element.

Props:
```typescript
interface StatusBadgeProps {
  status: 'completed' | 'ready_to_start' | 'parsing' | 'scoring' | string;
}
```

CSS class mapping:
| Status | Classes |
|---|---|
| `completed` | `bg-emerald-500/10 text-emerald-400 border border-emerald-500/20` |
| `ready_to_start` | `bg-indigo-500/10 text-indigo-400 border border-indigo-500/20` |
| `parsing` / `scoring` | `bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse` |
| unknown | `bg-zinc-500/10 text-zinc-400 border border-zinc-500/20` (fallback) |

Label text is derived by replacing underscores with spaces and title-casing the status string.

---

### `components/NewSessionModal.tsx` (`"use client"`)

A controlled overlay modal. Visibility is driven by the `open` prop from the parent.

Props:
```typescript
interface NewSessionModalProps {
  open: boolean;
  onClose: () => void;
}
```

Internal state:
```typescript
const [jobTitle, setJobTitle] = useState('');
const [jdText, setJdText] = useState('');
const [file, setFile] = useState<File | null>(null);
const [submitting, setSubmitting] = useState(false);
const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
const [submitError, setSubmitError] = useState<string | null>(null);
```

State reset: a `useEffect` watching `open` resets all state fields to defaults when `open` transitions to `false`.

#### File Upload Area

Supports both drag-and-drop and click-to-browse. Drag events handled: `onDragOver`, `onDragLeave`, `onDrop`. On file selection (either path), validates the extension is `.pdf` before storing in state. If invalid, sets a field error and does not update `file` state.

#### Client-Side Validation (pre-submit)

Runs synchronously before any network call:
1. `jobTitle.trim() === ''` → sets error on `jobTitle` field.
2. `jdText.trim() === ''` → sets error on `jdText` field.
3. `file === null` → sets error on `file` field.

If any error is set, the function returns early without calling `fetch`.

#### Submission Flow

```
1. Run client-side validation → abort if errors
2. setSubmitting(true), clear previous submitError
3. Build FormData: append 'file' + 'jd_text'
4. POST to http://localhost:8000/api/v1/practice/initialize
5a. On success (201): extract session_id → router.push(`/practice/${session_id}`)
5b. On error: setSubmitError(message), setSubmitting(false)
```

The submit button is `disabled` and shows a spinner icon (`lucide-react Loader2` with `animate-spin`) while `submitting === true`.

---

### `lib/api.ts`

Thin typed wrappers around `fetch` to keep component code clean.

```typescript
export async function fetchSessions(): Promise<SessionSummary[]>
export async function initializeSession(formData: FormData): Promise<{ session_id: string }>
```

Both functions throw a typed `ApiError` on non-2xx responses, carrying the HTTP status and the parsed error detail string from the backend JSON body.

---

### `types/session.ts`

TypeScript interfaces mirroring the backend Pydantic response models:

```typescript
export interface JobSummary {
  id: string;
  title: string;
}

export interface SessionSummary {
  session_id: string;
  status: string;
  created_at: string;
  job: JobSummary;
  resume_score: number | null;
}
```

---

## Data Models

### API Contracts Consumed

#### `GET /api/v1/practice/sessions` → `SessionSummary[]`

```json
[
  {
    "session_id": "uuid-string",
    "status": "completed",
    "created_at": "2024-01-15T10:30:00Z",
    "job": { "id": "uuid-string", "title": "Senior Software Engineer" },
    "resume_score": 82
  }
]
```

#### `POST /api/v1/practice/initialize` → `InitializeSessionResponse`

Request: `multipart/form-data` with fields `file` (PDF binary) and `jd_text` (string).

```json
{
  "session_id": "uuid-string",
  "job_id": "uuid-string",
  "status": "parsing",
  "message": "Practice session initialized..."
}
```

---

## Error Handling

| Scenario | Component | Handling |
|---|---|---|
| `GET /sessions` network failure | Dashboard | Sets `error` state, renders error banner |
| `GET /sessions` returns empty array | SessionGrid | Renders empty-state message |
| Invalid file type selected | NewSessionModal | Sets field error, does not store file |
| Form submitted without required fields | NewSessionModal | Sets per-field errors, blocks network call |
| `POST /initialize` non-2xx response | NewSessionModal | Sets `submitError`, re-enables submit button |
| `POST /initialize` network failure | NewSessionModal | Sets `submitError`, re-enables submit button |

---

## Testing Strategy

Verification focuses on component rendering behavior and form validation logic, not end-to-end network calls.

- `SessionGrid` with an empty array renders the empty-state message without throwing.
- `SessionGrid` with a mock session array renders the correct number of rows.
- `StatusBadge` renders the correct CSS classes for each known status value.
- `NewSessionModal` submit without a file shows the file validation error and does not call `fetch`.
- `NewSessionModal` submit without a job title shows the title validation error.
- `NewSessionModal` disables the submit button and shows a spinner while `submitting` is `true`.
