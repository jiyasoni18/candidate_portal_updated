# Frontend Phase 2: Async State Polling Loop & Pre-Interview Alignment Report View

## 1. Objective
Implement the Next.js waiting room layout that tracks backend processing milestones via an asynchronous client polling loop. Once processing finishes, this view renders the comprehensive 100-point resume-to-JD alignment dashboard card, exposing core candidate strengths, alignment gaps, and the custom interview session launcher.

## 2. Technical Stack & Dependencies
- **Framework Modules**: Next.js Client Component (`"use client"`), tracking state hooks (`useState`, `useEffect`, `useRef`).
- **Data Hydration**: Standard browser `fetch` utilities targeting the single session reading router.

---

## 3. Component Architecture & Logic Specs (`app/practice/[session_id]/page.tsx`)

### 3.1. Asynchronous Client-Side Polling Engine
- **Lifecycle Setup**: On component layout mount, extract the `session_id` route parameter and kick off a safe, browser-native `setInterval` execution loop pulsing every 3000ms (3 seconds).
- **Execution Hook**: The polling loop must query `GET http://localhost:8000/api/v1/practice/session/${session_id}`.
- **State Switch Conditions**:
  - While the response returns `status: "parsing"` or `status: "scoring"`, keep the UI locked inside an animated loading canvas state.
  - As soon as the payload response shifts to `status: "ready_to_start"`, clear the active interval memory reference using `clearInterval` instantly to prevent unnecessary background network pollution. Hydrate the page state arrays with the complete `resume_report` JSON parameters.

### 3.2. Processing / Loading State UI Canvas
- **Visual Design**: Render an immersive, centered processing column layout inside our slate-900 theme palette.
- **Interactive Elements**: Use a dynamic progress loop or pulse tracker showing current system actions:
  - **If Status is `'parsing'`**: Display message: *"Aria is parsing your resume structural text layout..."*
  - **If Status is `'scoring'`**: Display message: *"Gemini is cross-referencing your background history against the target Job Description..."*

### 3.3. Premium Alignment Report Dashboard Card View
Once status hits `'ready_to_start'`, unlock the workspace components and render three key sections cleanly:
- **Section A: The Score Meter Card**: Display a large, premium visual dial or bold circle badge showing the `resume_report.score` out of 100. Apply conditional text coloring:
  - $\ge 75$: High alignment (Emerald green highlights)
  - $\ge 60$: Moderate alignment (Indigo/violet highlights)
  - $< 60$: Gaps flagged (Amber/orange highlights)
- **Section B: Core Strengths & Alignment Gaps**:
  - Map `resume_report.strengths` array elements into a responsive flex layout card accompanied by green checkmark icons.
  - Map `resume_report.weaknesses` array elements into a matching flex card accompanied by amber alert or negative indicator icons to clearly highlight target preparation gaps.
- **Section C: Action Tracker Link**: Render a crisp, prominent button at the bottom labeled **"Enter AI Practice Interview Booth"**. Clicking this component navigates the browser router directly forward to the real-time interaction view at: `/interview/${session_id}`.

---

## 4. Verification Check Constraints
The Kiro agent must verify successful completion by asserting:
1. Ensure the active `setInterval` cleanup function binds tightly into the React component unmount hook (`return () => clearInterval(...)`) to eliminate ghost window network leak paths.
2. Confirm that attempting to poll or read a session with an invalid UUID structure renders an elegant error boundary dashboard link instead of hanging the candidate workspace into a permanent loading loop.