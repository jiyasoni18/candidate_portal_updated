# Requirements Document

## Introduction

Phase 4 implements the asynchronous multi-stage background processing pipeline that is triggered immediately after a practice session is initialized in Phase 3. The pipeline runs entirely inside FastAPI's native `BackgroundTasks` mechanism and executes three sequential stages: PDF text extraction via PyMuPDF, resume parsing via the Gemini LLM (through OpenRouter), and a combined alignment scoring and question generation stage. At each milestone the pipeline commits intermediate state back to the `practice_sessions` PostgreSQL table, transitioning the session status from `'parsing'` → `'scoring'` → `'ready_to_start'`. No HTTP response is blocked by this pipeline; it runs entirely after the `201 Created` response from Phase 3 has been returned to the caller.

---

## Glossary

- **Background Pipeline**: The async function registered with FastAPI's `BackgroundTasks` that orchestrates all three processing stages for a given session.
- **Session ID**: The UUID that uniquely identifies a row in `practice_sessions` and the subdirectory under `./storage/resumes/` where the resume PDF is stored.
- **Job ID**: The UUID that uniquely identifies the associated row in `practice_jobs`, which holds the raw `jd_text`.
- **Resume File Path**: The local filesystem path `./storage/resumes/{session_id}/resume.pdf` where the uploaded PDF is stored.
- **Raw Resume Text**: The plain-text string extracted from the PDF by PyMuPDF, capped at 25,000 characters.
- **Resume Parsed Data**: The structured JSON object conforming to `schemas/resume.py::ResumeParsedData`, produced by Pipeline 1 and stored in `practice_sessions.resume_parsed`.
- **Resume Report Data**: The structured JSON object conforming to `schemas/resume.py::ResumeReportData`, containing the alignment score (0–100), reference summary, strengths, and weaknesses, stored in `practice_sessions.resume_report`.
- **Generated Questions**: The validated array of exactly 8 `GeneratedQuestionItem` objects conforming to `schemas/questions.py::QuestionArraySchema`, stored in `practice_sessions.generated_questions`.
- **Pipeline 1**: The resume profile conversion stage that calls the Gemini LLM via OpenRouter to convert Raw Resume Text into Resume Parsed Data.
- **Pipeline 2**: The alignment evaluator and question generation stage that calls the Gemini LLM via OpenRouter to produce Resume Report Data and Generated Questions from Resume Parsed Data and the JD text.
- **OpenRouter**: The HTTP API gateway used to route LLM requests to the Gemini lite-tier model.
- **Gemini**: The LLM model (lite tier variant) accessed via OpenRouter for both Pipeline 1 and Pipeline 2.
- **DB Client**: The `asyncpg` connection acquired from the application-level connection pool, used to execute UPDATE statements within the background task.
- **`parsing` Status**: The initial `practice_sessions.status` value set in Phase 3, indicating the background pipeline has been triggered but not yet started.
- **`scoring` Status**: The intermediate `practice_sessions.status` value written after Pipeline 1 completes, indicating resume parsing is done and alignment scoring is in progress.
- **`ready_to_start` Status**: The terminal `practice_sessions.status` value written after Pipeline 2 completes, indicating all data is ready for the candidate to begin the interview.
- **Question Category**: One of the string literals `'opening'`, `'experience'`, `'rolefit'`, `'behavioral'`, `'situational'`, or `'closing'`, assigned to each generated question.
- **Expected Duration**: The integer number of seconds assigned to each generated question as a default response timer (120 or 150 seconds).
- **`process_session_background` Function**: The top-level async function that serves as the `BackgroundTasks` callback entry point, accepting `session_id`, `job_id`, and `file_path` as arguments.

---

## Requirements

### Requirement 1

**User Story:** As a backend developer, I want a single async background function to orchestrate all processing stages, so that the pipeline is invoked as a single `BackgroundTasks` callback and manages its own state transitions.

#### Acceptance Criteria

1. THE Background Pipeline SHALL expose a single async function named `process_session_background` that accepts `session_id` (UUID), `job_id` (UUID), and `file_path` (str) as its parameters.
2. WHEN the Phase 3 initialization handler commits its database transaction, THE Background Pipeline SHALL be registered as a `BackgroundTasks` callback with `session_id`, `job_id`, and `file_path` as arguments.
3. THE Background Pipeline SHALL execute Pipeline 1 and Pipeline 2 in strict sequential order, where Pipeline 2 does not begin until Pipeline 1 has completed and its results have been committed to the database.
4. IF any unhandled exception occurs at any stage of the pipeline, THEN THE Background Pipeline SHALL catch the exception, log the error with the `session_id`, and SHALL NOT propagate the exception in a way that crashes the FastAPI worker process.

---

### Requirement 2

**User Story:** As a backend developer, I want the pipeline to extract raw text from the stored PDF using PyMuPDF, so that the text content is available for LLM processing without blocking the event loop.

#### Acceptance Criteria

1. THE Background Pipeline SHALL use the `pymupdf` (`fitz`) library to open the PDF file at the `file_path` and extract text from all pages.
2. THE Background Pipeline SHALL concatenate the extracted text from all pages into a single string and truncate the result to a maximum of 25,000 characters.
3. IF the PDF file does not exist at `file_path` or cannot be opened by PyMuPDF, THEN THE Background Pipeline SHALL log the error and terminate the pipeline for that session without updating the session status.
4. THE Background Pipeline SHALL perform PDF text extraction in a way that does not block the asyncio event loop (e.g., using `asyncio.to_thread` or an executor).

---

### Requirement 3

**User Story:** As a backend developer, I want Pipeline 1 to send the raw resume text to the Gemini LLM via OpenRouter and receive a structured JSON response matching the `ResumeParsedData` schema, so that the resume is converted into a machine-readable format.

#### Acceptance Criteria

1. THE Background Pipeline SHALL send an HTTP POST request to the OpenRouter API endpoint using the Gemini lite-tier model identifier, with the Raw Resume Text injected into a structured system prompt that instructs the model to return exclusively valid JSON.
2. THE Background Pipeline SHALL validate the LLM response body against the `ResumeParsedData` Pydantic v2 model defined in `schemas/resume.py`.
3. WHEN Pipeline 1 produces a valid `ResumeParsedData` object, THE Background Pipeline SHALL serialize it to a JSON string and write it to `practice_sessions.resume_parsed`, and SHALL update `practice_sessions.status` to `'scoring'` in a single atomic database UPDATE.
4. IF the OpenRouter API call fails (network error, non-200 response, or timeout), THEN THE Background Pipeline SHALL log the error with the `session_id` and terminate the pipeline without advancing the session status.
5. IF the LLM response body cannot be parsed into a valid `ResumeParsedData` object, THEN THE Background Pipeline SHALL log the validation error and terminate the pipeline without advancing the session status.
6. WHERE the candidate's resume contains no certifications, THE Background Pipeline SHALL produce a `ResumeParsedData` object with an empty `certifications` list rather than failing validation.

---

### Requirement 4

**User Story:** As a backend developer, I want Pipeline 2 to send the parsed resume JSON and the JD text to the Gemini LLM via OpenRouter and receive a structured response containing both the alignment report and the 8 generated questions, so that the session is fully prepared for the candidate.

#### Acceptance Criteria

1. THE Background Pipeline SHALL retrieve the `jd_text` for the session by querying `practice_jobs` using the `job_id` before invoking Pipeline 2.
2. THE Background Pipeline SHALL send an HTTP POST request to the OpenRouter API with the serialized `ResumeParsedData` JSON string and the `jd_text` injected into a structured system prompt.
3. THE Background Pipeline SHALL validate the alignment report portion of the LLM response against the `ResumeReportData` Pydantic v2 model defined in `schemas/resume.py`, which requires a `score` (integer 0–100), `reference_to_jd` (str), `strengths` (list of str), and `weaknesses` (list of str).
4. THE Background Pipeline SHALL validate the questions portion of the LLM response against the `QuestionArraySchema` Pydantic v2 model defined in `schemas/questions.py`, which requires exactly 8 `GeneratedQuestionItem` objects each with an `id`, `question`, `category`, and `expected_duration_seconds`.
5. WHEN Pipeline 2 produces valid `ResumeReportData` and `QuestionArraySchema` objects, THE Background Pipeline SHALL write the serialized `ResumeReportData` JSON to `practice_sessions.resume_report`, the serialized `QuestionArraySchema` JSON to `practice_sessions.generated_questions`, and SHALL update `practice_sessions.status` to `'ready_to_start'` in a single atomic database UPDATE.
6. IF the OpenRouter API call for Pipeline 2 fails, THEN THE Background Pipeline SHALL log the error with the `session_id` and terminate the pipeline, leaving `practice_sessions.status` as `'scoring'`.
7. IF the LLM response for Pipeline 2 cannot be validated against either `ResumeReportData` or `QuestionArraySchema`, THEN THE Background Pipeline SHALL log the validation error and terminate the pipeline, leaving `practice_sessions.status` as `'scoring'`.

---

### Requirement 5

**User Story:** As a backend developer, I want the generated questions to follow strict content and structural rules, so that the interview experience is personalized, conversational, and narrative-focused.

#### Acceptance Criteria

1. THE Background Pipeline SHALL instruct the LLM via the system prompt to generate exactly 8 questions in the following fixed narrative sequence: Q1 as a warm introduction, Q2–Q3 as resume-specific deep dives, Q4–Q6 as role alignment and situational questions, Q7 as a professional growth and transition question, and Q8 as a formal closing reflection.
2. THE Background Pipeline SHALL instruct the LLM via the system prompt that at least 4 of the 8 questions must reference specific tool combinations, repository names, or employer names extracted directly from the candidate's resume.
3. THE Background Pipeline SHALL instruct the LLM via the system prompt to use a conversational and informal tone, framing questions with openers such as "So" or "I noticed", and to avoid the following banned terms: "spearheaded", "honed", "leveraged", "cross-functional", "stakeholders", "robust", "deep dive".
4. THE Background Pipeline SHALL instruct the LLM via the system prompt to avoid all abstract or theoretical questions (such as conceptual definitions, language trivia, or direct coding queries) and to require every question to prompt the candidate to narrate actual background scenarios, past tools, or custom projects.
5. THE Background Pipeline SHALL assign each generated question a `category` value from the set `('opening', 'experience', 'rolefit', 'behavioral', 'situational', 'closing')` and an `expected_duration_seconds` value of either 120 or 150.

---

### Requirement 6

**User Story:** As a backend developer, I want the pipeline to use a dedicated OpenRouter client module, so that API key management, model selection, and HTTP retry logic are centralized and reusable across pipelines.

#### Acceptance Criteria

1. THE Background Pipeline SHALL use a dedicated async client module (e.g., `api/llm_client.py`) that encapsulates the OpenRouter base URL, API key (read from environment/config), and model identifier.
2. THE Background Pipeline SHALL read the OpenRouter API key from an environment variable or `config.py` settings object and SHALL NOT hardcode the key in any source file.
3. WHEN an OpenRouter API call returns a non-200 HTTP status code, THE Background Pipeline SHALL log the status code and response body, then raise an exception that the calling pipeline stage can catch.

---

### Requirement 7

**User Story:** As a backend developer, I want a mock-based verification script for the pipeline, so that the state transitions and schema validations can be confirmed without making live LLM API calls.

#### Acceptance Criteria

1. THE Background Pipeline SHALL be verifiable via a script at `scripts/verify_phase4.py` that mocks the OpenRouter HTTP calls and exercises the full pipeline against a real PostgreSQL database connection.
2. WHEN the verification script runs, THE Background Pipeline SHALL transition a test session's status from `'parsing'` to `'scoring'` to `'ready_to_start'` in the correct order.
3. WHEN the verification script runs, THE Background Pipeline SHALL populate `practice_sessions.resume_parsed`, `practice_sessions.resume_report`, and `practice_sessions.generated_questions` with valid JSON conforming to their respective Pydantic schemas.
4. WHEN the verification script runs, THE Background Pipeline SHALL complete without raising an unhandled exception.
