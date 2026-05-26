# Implementation Plan

- [x] 1. Add `GRADING_MODEL` config setting and extend `call_openrouter` with model override





  - Add `GRADING_MODEL: str = "anthropic/claude-3.5-sonnet"` to `config.py` Settings class
  - Add optional `model: str | None = None` parameter to `call_openrouter` in `api/llm_client.py`; use `model or settings.OPENROUTER_MODEL` in the payload
  - _Requirements: 7.1, 7.2, 7.3_

- [x] 2. Implement the grading pipeline in `services/background_pipeline.py`





- [x] 2.1 Add `count_candidate_turns` and `map_verdict` pure helpers


  - `count_candidate_turns(transcript)`: count turns where `speaker == "candidate"` and `text.strip()` is non-empty
  - `map_verdict(score)`: apply the 80/68/52 threshold mapping to return the correct verdict string
  - _Requirements: 2.1, 4.1, 4.2, 4.3, 4.4_

- [x] 2.2 Add `build_grading_prompt` function

  - Construct system prompt instructing the LLM to score exactly 4 dimensions (`technical`, `role_alignment`, `communication`, `presence`) with defined weights
  - Embed the Technical Familiarity constraint: gaps array must only contain skills discussed in the transcript
  - Instruct LLM to return exactly 3 `technical_round_probes` tailored to transcript content
  - Instruct LLM NOT to include `overall_score`, `completion_ratio`, or `practice_verdict` (computed server-side)
  - Serialize `jd_text`, `resume_parsed`, and `transcript` as the user content JSON
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 5.1, 5.2_

- [x] 2.3 Replace `grade_session_background` stub with full implementation

  - Fetch `transcript`, `resume_parsed`, `job_id` from `practice_sessions` by `session_id`; log and return if not found or transcript is null
  - Fetch `jd_text` from `practice_jobs`; log and return if not found
  - Call `count_candidate_turns` → compute `completion_ratio = min(questions_answered / 8, 1.0)`
  - Call `call_openrouter` with `build_grading_prompt` output and `model=settings.GRADING_MODEL`
  - Validate LLM response with `InterviewAssessmentSchema.model_validate_json`; log and return on failure
  - Compute `weighted_raw` and `final_score = max(0, min(100, round(weighted_raw * completion_ratio)))`
  - Overwrite `overall_score`, `completion_ratio`, `practice_verdict`, `turns_analyzed` on the validated model using `model_copy`
  - Execute single atomic `UPDATE practice_sessions SET interview_assessment=$1, status='completed' WHERE id=$2`
  - Wrap entire function in `try/except Exception` matching existing pipeline pattern
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.2, 2.3, 2.4, 2.5, 3.5, 6.1, 6.3_

- [x] 3. Expose `interview_assessment` in the session detail endpoint





  - Update `SessionDetailResponse` in `api/routers/practice.py` to include `interview_assessment: Optional[dict] = None`
  - Update the `GET /practice/session/{session_id}` SQL query to also select `ps.interview_assessment`
  - Add `"completed"` and `"interview_processing"` to `_ACTIVE_STATUSES` if not already present, and expose `interview_assessment` when status is `completed`
  - _Requirements: 6.2_

- [x] 4. Write verification test for completion-ratio math and happy path





- [x] 4.1 Write unit tests for helpers and pipeline


  - Test `count_candidate_turns` with mixed turns, empty text, and agent-only transcripts
  - Test `map_verdict` at all four threshold boundaries (51, 52, 67, 68, 79, 80)
  - Test 4-of-8 scenario: mock transcript with 4 candidate turns → assert `completion_ratio == 0.5` and `final_score == round(weighted_raw * 0.5)`
  - Test happy path: mock `db_pool` and `call_openrouter` returning valid JSON → assert DB UPDATE called with `status='completed'`
  - Test LLM validation failure: mock `call_openrouter` returning malformed JSON → assert DB UPDATE NOT called
  - Test session not found: mock DB returning `None` → assert no exception raised
  - _Requirements: 2.5, 1.3, 3.5, 6.3_
