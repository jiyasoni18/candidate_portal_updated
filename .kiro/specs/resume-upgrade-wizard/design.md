# Design Document: Resume Upgrade Wizard

## Overview

The Resume Upgrade Wizard adds a self-contained improvement flow to the existing Alignment Report page. A new "Upgrade Resume" button navigates the candidate to `/practice/[session_id]/upgrade`, where they:

1. Review AI-detected gaps and fill in notes for each
2. Select terminology improvements via checkboxes
3. Add custom content (with "about me:" prefix support for professional summary)
4. Click "Refine My Inputs" — a single `/refine` API call processes everything
5. Review each refined item (gap paragraphs + custom addition items) with per-item approve/reject controls
6. Click "Generate Upgraded Resume" — only approved items are sent to the `/pdf` endpoint
7. Download the ATS-optimized PDF

Hyperlinks and URLs provided by the candidate in any input field are preserved through the entire pipeline and rendered as clickable links in the PDF.

---

## Architecture

```
Alignment Report Page (/practice/[session_id])
  └── "Upgrade Resume" button (status === ready_to_start)
        └── navigates to /practice/[session_id]/upgrade

Resume Upgrade Wizard Page (/practice/[session_id]/upgrade)
  ├── Step 1 — Input Collection
  │     ├── Fetches session via GET /api/v1/practice/session/{session_id}
  │     │     └── reads enhanced_analysis.gaps, enhanced_analysis.improvements
  │     ├── Gap cards (one textarea per gap)
  │     ├── Improvements checkboxes
  │     ├── Custom additions textarea (supports about_me: prefix)
  │     ├── Template picker
  │     └── "Refine My Inputs" button
  │           └── POST /api/v1/practice/session/{session_id}/refine
  │                 body: { custom_additions, gap_selections, selected_improvements }
  │                 response: { gaps: { "0": "refined...", ... }, custom: "refined..." }
  │
  └── Step 2 — Refinement Review
        ├── One card per refined gap paragraph (approve/reject)
        ├── One card per refined custom addition item (approve/reject)
        ├── Template picker (still editable)
        └── "Generate Upgraded Resume" button
              └── GET /api/v1/practice/session/{session_id}/pdf?template=<name>
                    query params: accepted_gaps, accepted_custom (only approved items)
                    → triggers browser download
```

### Data Flow

1. Page mounts → `fetchSession(sessionId)` → reads `enhanced_analysis.gaps` and `enhanced_analysis.improvements`.
2. Candidate fills gap notes, checks/unchecks improvements, types custom additions, selects template.
3. On "Refine My Inputs":
   - Build `gap_selections` map: `{ "0": noteForGap0, ... }` — only gaps with notes.
   - Build `selected_improvements` array from checked improvement strings.
   - Call `refineWithGaps(sessionId, customAdditions, gapSelections, selectedImprovements)`.
   - Transition to Step 2 with the returned `{ gaps, custom }` data.
4. On "Generate Upgraded Resume":
   - Collect only approved gap paragraphs and approved custom items.
   - Pass them to `generatePDF(sessionId, template, approvedGaps, approvedCustom)`.
   - Trigger download via `URL.createObjectURL(blob)`.

---

## Components and Interfaces

### Updated File: `frontend/app/practice/[session_id]/upgrade/page.tsx`

The page now has two logical steps controlled by a `step: "input" | "review"` state variable.

**Step 1 sub-components (unchanged from current):**

| Component | Responsibility |
|---|---|
| `GapCard` | Renders one gap with description and textarea for candidate note |
| `ImprovementsList` | Renders all improvements as checkboxes |
| `CustomAdditionsField` | Textarea with helper hint (including about me: prefix hint) |
| `TemplatePicker` | Button group for selecting PDF template |

**Step 2 sub-components (new):**

| Component | Responsibility |
|---|---|
| `RefinedItemCard` | Renders one refined item (gap or custom) with Approve/Reject buttons and visual state |
| `RefinementReviewStep` | Renders all `RefinedItemCard`s grouped by type, plus the Generate button |

**Page-level state additions:**

```typescript
// Step 1 (existing)
gapNotes: Record<string, string>
selectedImprovements: Set<number>
customAdditions: string
selectedTemplate: Template
isRefining: boolean          // replaces isGenerating for the refine call
refineError: string | null

// Step 2 (new)
step: "input" | "review"
refinedGaps: Record<string, string>      // index → refined paragraph from LLM
refinedCustomItems: string[]             // array of refined custom addition lines
approvedGaps: Set<string>               // indices of approved gap items
approvedCustomItems: Set<number>        // indices of approved custom items
isGenerating: boolean
generateError: string | null
```

### `RefinedItemCard` component

```typescript
function RefinedItemCard({
  label,
  content,
  approved,
  onApprove,
  onReject,
}: {
  label: string;
  content: string;
  approved: boolean | null;  // null = default (approved), true = approved, false = rejected
  onApprove: () => void;
  onReject: () => void;
})
```

Visual states:
- Default / approved: normal card with green "Approved" badge, Approve button highlighted
- Rejected: dimmed card (`opacity-50`) with red "Rejected" badge, Reject button highlighted

### Updated File: `frontend/lib/api.ts`

The existing `refineWithGaps` function signature stays the same. The `generatePDF` function needs to accept approved content to pass to the backend:

```typescript
export async function generatePDF(
  sessionId: string,
  template?: string,
  approvedGaps?: string,      // newline-joined approved gap paragraphs
  approvedCustom?: string     // newline-joined approved custom items
): Promise<Blob>
```

The PDF endpoint already accepts `accepted_texts` and `custom_text` via the backend — these are passed as query params or the wizard calls a new overload. Since the PDF endpoint is a GET, approved content is passed by first calling a lightweight PATCH/update or by re-using the refine endpoint to persist only approved items before calling PDF. 

**Revised approach:** After the candidate approves items, call `POST /refine` a second time with only the approved content to persist it, then call `GET /pdf`. This keeps the backend stateless and avoids adding query params with large text bodies to a GET request.

**Final approach (simplest):** The `/refine` endpoint already persists the refined content to `enhanced_analysis`. After the review step, call `POST /refine` again with only the approved gap paragraphs (as pre-refined text, not raw notes) and approved custom items. The backend stores them, then `GET /pdf` reads from the stored state. To support passing pre-refined text directly (bypassing LLM re-processing), add a `pre_refined: bool` flag to `RefineCustomAdditionsRequest` — when `true`, the backend skips the LLM call and stores the provided content directly.

### Backend: `api/routers/practice.py`

Add `pre_refined: Optional[bool] = False` to `RefineCustomAdditionsRequest`. When `pre_refined=True`:
- Skip the `refine_custom_additions` LLM call
- Store `gap_selections` values directly as the refined gap content in `enhanced_analysis.gaps`
- Store `custom_additions` directly in the `custom_additions` column

### Backend: `services/enhanced_analyzer.py`

The `refine_custom_additions` function currently returns `{ "gaps": { "0": "...", "1": "..." }, "custom": "..." }`. The custom field is a single string. To support per-item approve/reject on the frontend, the backend should split the custom additions into individual items before returning.

Add a `split_custom_items` helper that splits the refined `custom` string by newline into a list, so the frontend can render one card per item.

Update `RefineCustomAdditionsResponse` to include:
```python
refined_gaps: Optional[Dict[str, str]] = None    # index → refined paragraph
refined_custom_items: Optional[List[str]] = None  # list of refined custom lines
```

---

## Data Models

### Updated `RefineCustomAdditionsRequest`

```python
class RefineCustomAdditionsRequest(BaseModel):
    custom_additions: str
    gap_selections: Optional[Dict[str, str]] = None
    selected_improvements: Optional[List[str]] = None
    pre_refined: Optional[bool] = False   # NEW: skip LLM, store directly
```

### Updated `RefineCustomAdditionsResponse`

```python
class RefineCustomAdditionsResponse(BaseModel):
    session_id: UUID
    status: str
    enhanced_analysis: Optional[dict] = None
    refined_gaps: Optional[Dict[str, str]] = None        # NEW
    refined_custom_items: Optional[List[str]] = None     # NEW
```

### Frontend `refineWithGaps` return type

```typescript
interface RefineResponse {
  session_id: string;
  status: string;
  enhanced_analysis?: Record<string, unknown>;
  refined_gaps?: Record<string, string>;
  refined_custom_items?: string[];
}
```

---

## About Me Handling

When the candidate writes content prefixed with `about me:` (case-insensitive) in the Custom Additions field, the frontend passes it as-is to the `/refine` endpoint. The `refine_custom_additions` LLM prompt already instructs the model to preserve prefixes. The `generate_ats_pdf` prompt already has a rule that the Professional Summary is mandatory and should incorporate user-provided summary content. 

To make this explicit, the PDF generation prompt will be updated to add: "If Custom Additions contain a line prefixed with 'about me:', treat that content as additional professional summary material and merge it into the PROFESSIONAL SUMMARY section."

This requires no schema change — it is a prompt engineering update in `services/enhanced_analyzer.py`.

---

## Hyperlink Handling

The PDF generation prompt already contains rule 9: "HYPERLINKS & BACKLINKING: If the original resume or Custom Additions contain any hyperlinks/URLs... format them as clickable HTML tags." This rule already covers URLs passed through gap notes and custom additions. No additional backend changes are needed beyond ensuring the frontend does not strip URLs before sending them to `/refine`.

The `/refine` LLM prompt will be updated to add: "If the user's notes or custom additions contain URLs or hyperlinks, preserve them exactly as provided in your refined output."

---

## Error Handling

| Scenario | Handling |
|---|---|
| Session fetch fails on mount | Show error state with "Back to Report" link |
| Session has no gaps | Hide gaps section, show "No gaps detected" message |
| Session has no improvements | Hide improvements section entirely |
| `/refine` call fails (Step 1) | Show inline error, re-enable "Refine My Inputs" button |
| `/refine` call fails (Step 2 persist) | Show inline error, re-enable "Generate Upgraded Resume" button |
| `/pdf` call fails | Show inline error, re-enable generate button |
| PDF download fails (blob error) | Show inline error message |
| All items rejected | Allow PDF generation with improvements only; show info message |

---

## Testing Strategy

- Unit test `RefinedItemCard` renders approved/rejected visual states correctly.
- Unit test approve/reject toggles update state correctly.
- Integration test: mock `refineWithGaps` returning `{ refined_gaps, refined_custom_items }` — verify Step 2 renders correct number of cards.
- Integration test: verify only approved items are included in the second `/refine` call payload.
- Test error state: mock `/refine` returning 500 — verify error message appears and button re-enables.
- Test about me: verify content prefixed `about me:` is passed through without stripping.

---

## Design Decisions

**Why a two-step flow (input → review) instead of inline editing?**
Showing the LLM's refined output before committing to PDF generation gives the candidate control and builds trust. Inline editing would require re-running the LLM on every change, which is expensive and slow.

**Why call `/refine` twice (once to get refined content, once to persist approved items)?**
The first call returns the LLM-refined text for review. The second call (with `pre_refined=True`) persists only the approved items without re-running the LLM. This avoids adding large text bodies to a GET request and keeps the PDF endpoint stateless.

**Why `pre_refined` flag instead of a new endpoint?**
Minimal backend surface area. The refine endpoint already handles persistence logic; adding a flag is less disruptive than a new route.

**Why not pass approved content as query params to the PDF GET endpoint?**
Refined gap paragraphs can be hundreds of characters each. Query params are not suitable for large text payloads. Persisting via `/refine` first is cleaner.

**About Me as Professional Summary**
Candidates naturally write "About Me" sections. Treating this as professional summary content is the correct resume convention. A prompt-level rule is sufficient — no schema change needed.
