# Implementation Plan

- [x] 1. Extend config and add OpenRouter LLM client





  - Add `OPENROUTER_API_KEY` (required, no default) and `OPENROUTER_MODEL` (default `"google/gemini-flash-1.5"`) to `config.py`
  - Create `api/llm_client.py` with an async `call_openrouter(system_prompt, user_content) -> str` function using `httpx.AsyncClient`, `response_format: json_object`, 120s timeout, and `raise_for_status()`
  - _Requirements: 6.1, 6.2, 6.3_

- [x] 2. Implement the background pipeline service





- [x] 2.1 Create `services/__init__.py` and `services/background_pipeline.py` with document extraction


  - Implement `extract_resume_text(file_path: str) -> str` using `fitz` (pymupdf) inside `asyncio.to_thread`, truncating output to 25,000 characters
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 2.2 Implement Pipeline 1 — resume parser stage


  - Implement `build_resume_parser_prompt() -> str` returning the structured system prompt that enforces `ResumeParsedData` JSON output with empty arrays for missing fields
  - Implement `run_pipeline_1(raw_text: str) -> ResumeParsedData` calling `call_openrouter` and validating with `ResumeParsedData.model_validate_json`
  - _Requirements: 3.1, 3.2, 3.5, 3.6_

- [x] 2.3 Implement Pipeline 2 — alignment evaluator and question generator stage


  - Implement `build_pipeline_2_prompt() -> str` encoding all question content rules: 8-question narrative sequence, personalization rule (≥4 resume-specific), banned words, banned question types, category and duration assignments
  - Implement `run_pipeline_2(parsed_resume, jd_text) -> tuple[ResumeReportData, QuestionArraySchema]` calling `call_openrouter` and validating both `resume_report` and `questions` keys
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 2.4 Implement `process_session_background` orchestrator with DB writes and error handling


  - Implement the top-level `async def process_session_background(session_id, job_id, file_path, db_pool)` function that calls all three stages in sequence
  - After Pipeline 1 success: `UPDATE practice_sessions SET resume_parsed=$1, status='scoring' WHERE id=$2`
  - After Pipeline 2 success: `UPDATE practice_sessions SET resume_report=$1, generated_questions=$2, status='ready_to_start' WHERE id=$3`
  - Wrap the entire function body in a `try/except` that logs errors with `session_id` and never propagates exceptions
  - _Requirements: 1.1, 1.3, 1.4, 3.3, 3.4, 4.5, 4.6, 4.7_

- [x] 3. Wire the pipeline into the practice router





  - Replace the `run_processing_pipeline` stub in `api/routers/practice.py` with an import of `process_session_background` from `services/background_pipeline`
  - Update the `background_tasks.add_task` call to pass `request.app.state.db_pool` as the fourth argument
  - Add `request: Request` parameter to the `initialize_session` handler to access `app.state`
  - _Requirements: 1.2, 1.3_

- [x] 4. Create mock-based verification script





  - Create `scripts/verify_phase4.py` that inserts a test `practice_jobs` row and a `practice_sessions` row with `status='parsing'`, patches `api.llm_client.call_openrouter` with `AsyncMock` returning fixture JSON for both pipeline calls, runs `process_session_background` directly, then queries the DB to assert status is `'ready_to_start'` and all three JSONB columns are populated with schema-valid data
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [x] 4.1 Write unit tests for pipeline stages


  - Test `extract_resume_text` truncation at 25,000 characters
  - Test `run_pipeline_1` raises on API failure and on schema validation failure
  - Test `run_pipeline_2` raises on missing `resume_report` or `questions` keys
  - Test `process_session_background` terminates cleanly without raising on any stage failure
  - _Requirements: 1.4, 2.2, 3.4, 3.5, 4.6, 4.7_
