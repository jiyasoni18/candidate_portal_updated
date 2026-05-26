# Phase 3: Practice Session Initialization & Local File Upload Router

## 1. Objective
Build the main endpoint that candidates use to kick off a new interview. This route accepts an uploaded PDF resume and a text block containing the target Job Description, saves the asset locally to a structured filesystem directory, and logs initial rows into PostgreSQL.

## 2. Directory Layout & Requirements
Because this setup utilizes local storage infrastructure within Docker, ensure Kiro creates and mounts a persistent directory at the root:
- `./storage/resumes/`: Stores the uploaded PDF files.

## 3. Tech Stack Requirements (FastAPI + Asyncpg / SQLAlchemy)
- **HTTP Method**: `POST`
- **Route Path**: `/api/v1/practice/initialize`
- **Content Type**: `multipart/form-data`
- **Form Fields**:
  - `file`: `UploadFile` (The PDF Binary)
  - `jd_text`: `str` (The raw text of the target Job Description)
  - `user_id`: `UUID` (To mimic single-user context, default to the seeded test user ID: `a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d`)

## 4. Operational Step-by-Step Backend Logic
1. **Initialize IDs**: Generate unique UUIDs for the new `practice_jobs` record and `practice_sessions` record.
2. **Handle File Writes**: Save the incoming file stream to disk at `./storage/resumes/{session_id}/resume.pdf`. Ensure directories are created dynamically using `os.makedirs`.
3. **Database Transaction**:
   - Insert a row into `practice_jobs` capturing the pasted `description` and `title` (fallback title to "Target Job Role" if not provided).
   - Insert a row into `practice_sessions` linking back to the job, storing the local file path string under `resume_url`, setting `status` strictly to `'parsing'`, and leaving LLM artifacts as NULL.
4. **Instantly Hand Off**: Pass control immediately to FastAPI's native `BackgroundTasks` handler to execute the Phase 4 processing sequence, preventing an API block or timeout.
5. **Return Fast**: Immediately return a `201 Created` payload to the UI with the tracking identifier.

## 5. Expected API Payload Response Schema (`201 Created`)
```json
{
  "session_id": "d3c2b1a0-9f8e-7d6c-5b4a-3f2e1d0c9b8a",
  "job_id": "e4b11f20-80a8-48b6-b51f-6fa12a43312c",
  "status": "parsing",
  "message": "Practice session initialized. Async processing pipelines triggered successfully."
}

## 6. Verification Check Constraints
The Kiro agent must verify successful completion by testing the endpoint with a sample file using curl or a python request check script:

curl -X POST "http://localhost:8000/api/v1/practice/initialize" \
  -F "file=@sample_resume.pdf" \
  -F "jd_text=Seeking a Software Engineer experienced in Python and FastAPI..."

Verify that the entry exists in your running container's database and that the file was correctly stored in the local storage path.