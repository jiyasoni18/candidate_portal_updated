# Frontend Phase 1: Dashboard, Session Grid, & Multi-Part Asset Upload Modal

## 1. Objective
Build the Next.js layout infrastructure, a premium dark-mode candidate dashboard listing practice histories, and the core multi-part form upload component that captures and sends the resume PDF and target Job Description text to our local FastAPI instance.

## 2. Technical Stack & Dependencies
Ensure Kiro structures components with:
- **Framework**: Next.js 14+ (App Router, Client Components marked with `"use client"`).
- **Styling**: Tailwind CSS (Dark theme slate-900 palettes) with `lucide-react` for iconography.
- **Form Submission**: Native browser `FormData` wrappers.

---

## 3. UI Component Blueprint Specs

### 3.1. Master Layout & Sidebar Structure (`app/layout.tsx` & `components/Sidebar.tsx`)
- **Theme**: Fixed dark mode styling (`bg-slate-900 text-zinc-100 min-h-screen`).
- **Navigation Layout**: Persistent sidebar providing links to "Practice Dashboard", "Device Test Studio", and a "Settings/Profile" placeholder.

### 3.2. Main Candidate Dashboard Grid (`app/dashboard/page.tsx`)
- **Data Hook**: On component mounting (`useEffect`), fire a `GET` request to `http://localhost:8000/api/v1/practice/sessions`.
- **State Layout Elements**:
  - **Header Block**: Greeting display banner ("Welcome back, Candidate") coupled with a primary call-to-action button: **"+ New Practice Session"**.
  - **History Grid Card**: Renders historical interview rows dynamically. Columns mapped: Target Role Title, Created Date, Tracking Status Badge, and Performance Score.
  - **Status Badge Theme Classes**:
    - `'completed'`: Green pill (`bg-emerald-500/10 text-emerald-400 border border-emerald-500/20`).
    - `'ready_to_start'`: Indigo pill (`bg-indigo-500/10 text-indigo-400 border border-indigo-500/20`).
    - `'parsing'` / `'scoring'`: Animated yellow pulse wrapper (`bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse`).

### 3.3. Multi-Part Form Upload Modal (`components/NewSessionModal.tsx`)
- **UI Architecture**: Controlled modal state popping open via the dashboard CTA button.
- **Interactive Form Requirements**:
  - **Job Title Field**: String input default to placeholder text.
  - **Job Description Textarea**: Multiline text canvas block mapping to `jd_text`.
  - **Resume Drag-and-Drop Area**: Restricts accepting uploads strictly to valid `.pdf` extensions. Saves the local reference to component state as file binary arrays.
  - **Submit Button**: Changes to a disabled state showing a loading spinner when a request is active to prevent multi-hit race states.
- **API Request Integration**:
  - Assembles parameters into a unified form payload:
    ```typescript
    const formData = new FormData();
    formData.append("file", fileBinary);
    formData.append("jd_text", rawTextValue);
    ```
  - Sends a standard `POST` network hook to `http://localhost:8000/api/v1/practice/initialize`.
  - **Navigation Handoff**: Captures the returning successful JSON body, extracts the new unique `session_id`, and fires Next.js router instance methods to push paths forward instantly to: `/practice/${session_id}`.

---

## 4. Verification Check Constraints
The Kiro agent must verify successful completion by mocking local router rendering simulations:
1. Ensure components handle empty data list lookups gracefully without throwing undefined element array map exceptions or page breaks.
2. Confirm that hitting form upload triggers without choosing a file throws clear client-side validation hints before attempting backend execution requests.