# Implementation Plan

- [x] 1. Extend backend refine endpoint to accept selected improvements
  - Add `selected_improvements: Optional[List[str]]` field to `RefineCustomAdditionsRequest` in `api/routers/practice.py`
  - In the `/refine` handler, overwrite `enhanced_analysis["improvements"]` with the provided list before saving (only when the field is present)
  - _Requirements: 3.2, 3.3, 5.1_

- [x] 2. Return per-item refined results from the refine endpoint





  - Add `refined_gaps: Optional[Dict[str, str]]` and `refined_custom_items: Optional[List[str]]` to `RefineCustomAdditionsResponse` in `api/routers/practice.py`
  - After the LLM call in the `/refine` handler, populate `refined_gaps` from the LLM result and split the `custom` string by newline into `refined_custom_items`
  - Add `pre_refined: Optional[bool] = False` to `RefineCustomAdditionsRequest`; when `True`, skip the LLM call and store `gap_selections` values and `custom_additions` directly
  - _Requirements: 5.1, 5.3, 6.1_

- [x] 3. Update LLM prompts for about me and hyperlink handling





  - In `services/enhanced_analyzer.py`, update the `refine_custom_additions` prompt to add: preserve URLs/hyperlinks exactly as provided, and treat `about me:` prefixed content as professional summary material
  - In `generate_ats_pdf`, update the prompt to add: if Custom Additions contain a line prefixed with `about me:`, merge that content into the PROFESSIONAL SUMMARY section rather than placing it in additional sections
  - _Requirements: 4.4, 7.2, 7.3_

- [x] 4. Add `refineWithGaps` function to the API client
  - `refineWithGaps` in `frontend/lib/api.ts` already exists; update its return type to `RefineResponse` with `refined_gaps` and `refined_custom_items` fields
  - _Requirements: 5.1_

- [x] 5. Build the Refinement Review step in the wizard page









  - [x] 5.1 Add `RefinedItemCard` component to `frontend/app/practice/[session_id]/upgrade/page.tsx`


    - Renders label, refined content text, and Approve/Reject buttons
    - Approved state: normal card with green "Approved" badge; Reject button highlighted when rejected with dimmed card
    - Default state (no action taken) renders as approved
    - _Requirements: 5.4, 5.5, 5.6, 5.7_
  - [x] 5.2 Add step state and refinement review state to the page

    - Add `step: "input" | "review"` state
    - Add `refinedGaps`, `refinedCustomItems`, `approvedGaps`, `approvedCustomItems` state
    - _Requirements: 5.3_
  - [x] 5.3 Wire "Refine My Inputs" button to call `/refine` and transition to review step

    - Replace the current "Generate Upgraded Resume" single-step flow with a two-step flow
    - On click: set `isRefining=true`, call `refineWithGaps`, on success set `step="review"` with returned `refined_gaps` and `refined_custom_items`
    - On error: show inline error, re-enable button
    - _Requirements: 5.1, 5.2, 5.8_
  - [x] 5.4 Render the Refinement Review step with approve/reject cards


    - Show one `RefinedItemCard` per entry in `refinedGaps` (labeled with the original gap description)
    - Show one `RefinedItemCard` per entry in `refinedCustomItems`
    - Show "Generate Upgraded Resume" button below all cards
    - _Requirements: 5.3, 5.4, 6.5_



- [x] 6. Wire the generate flow to use only approved items



  - On "Generate Upgraded Resume" click: collect approved gap paragraphs and approved custom items
  - Call `POST /refine` with `pre_refined=True` and only the approved content to persist it
  - On success, call `generatePDF(sessionId, selectedTemplate)` to get the PDF blob
  - Trigger download via `URL.createObjectURL` + temporary `<a>` element click
  - On any error, set inline error state and re-enable the button
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 7. Update `generatePDF` in `frontend/lib/api.ts` return type and `refineWithGaps` return type




  - Update `refineWithGaps` return type to include `refined_gaps` and `refined_custom_items`
  - Ensure `generatePDF` still works with the existing signature (no changes needed if persist-first approach is used)
  - _Requirements: 5.1, 6.1_

- [x] 8. Add "Upgrade Resume" button to the Alignment Report page
  - In `frontend/app/practice/[session_id]/page.tsx`, add an "Upgrade Resume" button next to "Start Interview"
  - Button navigates to `/practice/${session.session_id}/upgrade`
  - _Requirements: 1.1, 1.2_
