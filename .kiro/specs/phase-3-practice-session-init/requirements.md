# Requirements Document

## Introduction

Phase 3 implements the `POST /api/v1/practice/initialize` endpoint — the entry point for every candidate practice session. This route accepts a multipart form submission containing a PDF resume file and a raw Job Description text block, persists the file to a structured local filesystem path under `./storage/resumes/`, inserts coordinated rows into the `practice_jobs` and `practice_sessions` PostgreSQL tables, and immediately hands off to a FastAPI `BackgroundTasks` handler before returning a `201 Created` response. The endpoint is intentionally non-blocking: all heavy LLM processing is deferred to Phase 4 background pipelines. This phase covers only the initialization, file I/O, database writes, and the fast-return contract.

## Glossary

- **Practice Session**: A single end-to-end interview practice run, represented by a row in the `practice_sessions` table and identified by a UUID `session_id`.
- **Practice Job**: A record in the `practice_jobs` table capturing the target Job Description text and an optional title, linked to a `user_id`.
- **Session ID**: A UUID generated at request time that uniquely identifies a `practice_sessions` row and is used as the subdirectory name for the uploaded resume file.
- **Job ID**: A UUID generated at request time that uniquely identifies a `practice_jobs` row.
- **Resume File**: A PDF binary uploaded via the `file` form field of the multipart request.
- **JD Text**: The raw plain-text Job Description string submitted via the `jd_text` form field.
- **Local Storage Path**: The filesystem path `./storage/resumes/{session_id}/resume.pdf` where the uploaded PDF is persisted inside the Docker container.
- **Initialization Router**: The FastAPI `APIRouter` module at `api/routers/practice.py` that registers the `POST /api/v1/practice/initialize` endpoint.
- **BackgroundTasks**: FastAPI's native `BackgroundTasks` utility injected into the path operation to schedule the Phase 4 processing pipeline without blocking the HTTP response.
- **InitializeSessionResponse**: The Pydantic v2 response model returned with HTTP `201 Created`, containing `session_id`, `job_id`, `status`, and `message`.
- **DB Client**: The asynchronous PostgreSQL connection utility (asyncpg-based) used to execute INSERT statements within the request handler.
- **Test User**: The seeded candidate with `user_id = a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d` defined in Phase 1's `init.sql`, used as the default `user_id` when none is provided.
- **`parsing` Status**: The initial string value written to `practice_sessions.status` at row creation time, indicating that background LLM pipelines have been triggered but not yet completed.

---

## Requirements

### Requirement 1

**User Story:** As a candidate, I want to submit my resume PDF and a Job Description text to a single endpoint, so that the system can initialize a new practice session and begin processing my materials in the background.

#### Acceptance Criteria

1. THE Initialization Router SHALL expose a `POST` endpoint at the path `/api/v1/practice/initialize` that accepts `multipart/form-data` content.
2. THE Initialization Router SHALL accept three form fields: `file` (PDF binary as `UploadFile`), `jd_text` (raw string), and `user_id` (UUID string, defaulting to `a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d` when not provided).
3. WHEN a request is received with a valid `file` and `jd_text`, THE Initialization Router SHALL return an HTTP `201 Created` response within 500 milliseconds, before any LLM or file-processing pipeline completes.
4. IF the `file` form field is absent from the request, THEN THE Initialization Router SHALL return an HTTP `422 Unprocessable Entity` response.
5. IF the `jd_text` form field is absent or empty, THEN THE Initialization Router SHALL return an HTTP `422 Unprocessable Entity` response.

---

### Requirement 2

**User Story:** As a backend developer, I want the uploaded resume PDF to be saved to a deterministic local path, so that downstream background pipelines can reliably locate and read the file by session ID.

#### Acceptance Criteria

1. THE Initialization Router SHALL generate a UUID `session_id` at request time and use it as the subdirectory name when constructing the storage path.
2. THE Initialization Router SHALL write the uploaded file binary to the path `./storage/resumes/{session_id}/resume.pdf` using non-blocking async file I/O.
3. WHEN the target directory `./storage/resumes/{session_id}/` does not exist, THE Initialization Router SHALL create it dynamically using `os.makedirs` with `exist_ok=True` before writing the file.
4. IF a file write operation fails due to a filesystem error, THEN THE Initialization Router SHALL return an HTTP `500 Internal Server Error` response and SHALL NOT insert any rows into the database.

---

### Requirement 3

**User Story:** As a backend developer, I want the endpoint to insert coordinated rows into `practice_jobs` and `practice_sessions`, so that the session is fully tracked in PostgreSQL from the moment of initialization.

#### Acceptance Criteria

1. THE Initialization Router SHALL insert one row into `practice_jobs` with the generated `job_id`, the provided `user_id`, the `jd_text` as `description`, and `"Target Job Role"` as the `title` fallback when no title is supplied.
2. THE Initialization Router SHALL insert one row into `practice_sessions` with the generated `session_id`, the provided `user_id`, the `job_id` from the preceding insert, the local file path string as `resume_url`, and `'parsing'` as the initial `status`.
3. WHEN both INSERT statements succeed, THE Initialization Router SHALL commit the transaction before triggering the background task.
4. IF either INSERT statement fails due to a database error, THEN THE Initialization Router SHALL roll back the transaction and return an HTTP `500 Internal Server Error` response.
5. THE Initialization Router SHALL leave the `resume_parsed`, `resume_report`, `generated_questions`, `livekit_room_name`, `transcript`, and `interview_assessment` columns as NULL at initialization time.

---

### Requirement 4

**User Story:** As a backend developer, I want the endpoint to immediately hand off to a background task after the database writes, so that the HTTP response is never blocked by LLM processing time.

#### Acceptance Criteria

1. WHEN the database transaction commits successfully, THE Initialization Router SHALL schedule the Phase 4 processing pipeline as a FastAPI `BackgroundTasks` callback, passing `session_id`, `job_id`, and the local file path as arguments.
2. THE Initialization Router SHALL return the `201 Created` response to the caller before the background task begins execution.
3. THE Initialization Router SHALL NOT await the background task function within the request handler scope.

---

### Requirement 5

**User Story:** As a backend developer, I want a typed Pydantic v2 response model for the `201 Created` payload, so that the API contract is explicit and serialization is consistent.

#### Acceptance Criteria

1. THE Initialization Router SHALL define an `InitializeSessionResponse` Pydantic v2 model with required fields: `session_id` (UUID), `job_id` (UUID), `status` (str), and `message` (str).
2. WHEN a practice session is successfully initialized, THE Initialization Router SHALL return an `InitializeSessionResponse` instance with `status` set to `"parsing"` and `message` set to `"Practice session initialized. Async processing pipelines triggered successfully."`.
3. THE `InitializeSessionResponse` model SHALL serialize `UUID` fields to string representations in the JSON response body.

---

### Requirement 6

**User Story:** As a backend developer, I want the FastAPI application entry point to mount the practice router under the `/api/v1` prefix, so that the endpoint is reachable at the correct versioned path.

#### Acceptance Criteria

1. THE FastAPI Application SHALL include a main application entry point at `main.py` that creates the `FastAPI` app instance.
2. THE FastAPI Application SHALL register the Initialization Router with the prefix `/api/v1` so that the full endpoint path resolves to `/api/v1/practice/initialize`.
3. THE FastAPI Application SHALL configure CORS middleware to allow requests from `http://localhost:3000` to support local frontend development.
