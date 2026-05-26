# Implementation Plan

- [x] 1. Set up project structure and configuration





  - Create `api/__init__.py`, `api/routers/__init__.py` to establish the package layout
  - Create `config.py` with a `pydantic-settings` `Settings` model exposing `DATABASE_URL` and `STORAGE_ROOT` with defaults matching the Phase 1 docker-compose credentials
  - Create `storage/resumes/.gitkeep` to ensure the storage directory is tracked but its contents are not
  - _Requirements: 6.1, 2.2_

- [x] 2. Implement the DB connection dependency and app entry point





- [x] 2.1 Create `api/dependencies.py` with the `get_db` asyncpg pool-acquire dependency


  - Implement `get_db(request: Request)` as an async generator that acquires a connection from `request.app.state.db_pool`
  - _Requirements: 3.1, 3.3_

- [x] 2.2 Create `main.py` with the FastAPI app factory


  - Implement the `asynccontextmanager` lifespan that creates and closes the `asyncpg` connection pool using `settings.DATABASE_URL`
  - Register CORS middleware allowing `http://localhost:3000`
  - Mount the practice router under prefix `/api/v1`
  - _Requirements: 6.1, 6.2, 6.3_

- [x] 3. Implement the practice initialization router





- [x] 3.1 Define the `InitializeSessionResponse` Pydantic v2 model in `api/routers/practice.py`


  - Fields: `session_id` (UUID), `job_id` (UUID), `status` (str), `message` (str)
  - Configure `json_encoders` to serialize UUID fields as strings
  - _Requirements: 5.1, 5.3_

- [x] 3.2 Implement the `POST /practice/initialize` endpoint handler

  - Accept `file: UploadFile`, `jd_text: str`, and `user_id: UUID` (with seeded test user default) as `Form` fields
  - Generate `session_id` and `job_id` UUIDs at request time
  - Write the uploaded file to `{STORAGE_ROOT}/{session_id}/resume.pdf` using `aiofiles`, calling `os.makedirs` with `exist_ok=True` first
  - Open an asyncpg transaction and INSERT into `practice_jobs` then `practice_sessions` with `status='parsing'` and NULL JSONB columns
  - Register the Phase 4 stub callback via `background_tasks.add_task` after the transaction commits
  - Return `InitializeSessionResponse` with HTTP status `201`
  - Wrap the handler body in a `try/except` that returns HTTP `500` on filesystem or database errors, with rollback on DB failure
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 5.2_

- [x] 3.3 Add a no-op Phase 4 background task stub


  - Define `async def run_processing_pipeline(session_id, job_id, file_path)` as a placeholder that logs its arguments
  - This stub will be replaced in Phase 4 without requiring changes to the router
  - _Requirements: 4.1, 4.3_

- [x] 3.4 Write integration tests for the initialization endpoint


  - Use `httpx.AsyncClient` with `ASGITransport` to test the endpoint against a real test database
  - Cover: successful 201 response shape, file written to disk, DB rows present, 422 on missing fields
  - _Requirements: 1.3, 1.4, 1.5, 2.2, 3.1, 3.2, 5.2_

- [x] 4. Create the Phase 3 verification script





  - Create `scripts/verify_phase3.py` that posts `sample_resume.pdf` to the running endpoint using `httpx`, prints the response, then queries the DB via `asyncpg` to confirm the `practice_jobs` and `practice_sessions` rows exist with correct values
  - _Requirements: 1.3, 3.1, 3.2_
