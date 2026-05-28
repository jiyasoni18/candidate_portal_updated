import json
import logging
import os
from datetime import datetime
from typing import Optional, Dict, List
from uuid import UUID, uuid4

import aiofiles
import asyncpg
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, field_serializer

from api.dependencies import get_db, get_current_user_id
from api.livekit_helper import LiveKitProvisionError, LiveKitTokenError, generate_token, provision_room
from config import settings
from schemas.livekit import RoomMetadataPayload, StartSessionResponse
from schemas.session_complete import SessionCompletePayload, SessionCompleteResponse
from services.background_pipeline import grade_session_background, process_session_background
from services.enhanced_analyzer import refine_custom_additions, generate_ats_pdf
from services.document_extraction import extract_url_text, extract_resume_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/practice", tags=["practice"])

# ---------------------------------------------------------------------------
# 3.1 Response model
# ---------------------------------------------------------------------------

class InitializeSessionResponse(BaseModel):
    model_config = ConfigDict()

    session_id: UUID
    job_id: UUID
    status: str
    message: str

    @field_serializer("session_id", "job_id")
    def serialize_uuid(self, v: UUID) -> str:
        return str(v)


# ---------------------------------------------------------------------------
# 5.1 Phase 5 response models
# ---------------------------------------------------------------------------

class JobSummary(BaseModel):
    id: UUID
    title: str
    company_name: Optional[str] = None

    @field_serializer("id")
    def serialize_uuid(self, v: UUID) -> str:
        return str(v)


class SessionSummary(BaseModel):
    session_id: UUID
    status: str
    created_at: datetime
    job: JobSummary
    resume_score: Optional[int] = None
    enhanced_metrics: Optional[dict] = None

    @field_serializer("session_id")
    def serialize_uuid(self, v: UUID) -> str:
        return str(v)


class SessionDetailResponse(BaseModel):
    session_id: UUID
    status: str
    created_at: datetime
    job: JobSummary
    resume_report: Optional[dict] = None
    generated_questions: Optional[list] = None
    interview_assessment: Optional[dict] = None
    enhanced_analysis: Optional[dict] = None
    transcript: Optional[list] = None

    @field_serializer("session_id")
    def serialize_uuid(self, v: UUID) -> str:
        return str(v)


# ---------------------------------------------------------------------------
# 5.4 Refine endpoint request/response models
# ---------------------------------------------------------------------------

class InitializeSessionRequest(BaseModel):
    job_title: str
    company_name: str = ""
    job_description: Optional[str] = None
    jd_type: str = "text"  # "text", "url", "file"
    jd_url: Optional[str] = None
    pre_refined: Optional[bool] = False


class ReanalyzeGapsRequest(BaseModel):
    custom_additions: str

class ReanalyzeGapsResponse(BaseModel):
    remaining_gaps: List[str]

class RefineCustomAdditionsRequest(BaseModel):
    custom_additions: str
    gap_selections: Optional[Dict[str, str]] = None
    selected_improvements: Optional[List[str]] = None
    pre_refined: Optional[bool] = False
    optimize_projects: Optional[bool] = False
    optimize_experience: Optional[bool] = False
    optimize_summary: Optional[bool] = False
    targeted_answers: Optional[Dict[str, str]] = None


class RefineCustomAdditionsResponse(BaseModel):
    session_id: UUID
    status: str
    enhanced_analysis: Optional[dict] = None
    refined_gaps: Optional[Dict[str, str]] = None
    refined_custom_items: Optional[List[str]] = None

    @field_serializer("session_id")
    def serialize_uuid(self, v: UUID) -> str:
        return str(v)


# ---------------------------------------------------------------------------
# 5.2 GET /practice/sessions list endpoint
# ---------------------------------------------------------------------------

@router.get("/sessions", response_model=list[SessionSummary])
async def list_sessions(
    user_id: UUID = Depends(get_current_user_id),
    conn: asyncpg.Connection = Depends(get_db),
) -> list[SessionSummary]:
    """Return all practice sessions for the current user, newest first."""
    try:
        rows = await conn.fetch(
            """
            SELECT
                ps.id          AS session_id,
                ps.status,
                ps.created_at,
                ps.resume_report,
                ps.enhanced_analysis,
                pj.id          AS job_id,
                pj.title       AS job_title,
                pj.company_name AS company_name
            FROM practice_sessions ps
            INNER JOIN practice_jobs pj ON ps.job_id = pj.id
            WHERE ps.user_id = $1
            ORDER BY ps.created_at DESC
            """,
            user_id,
        )
    except asyncpg.PostgresError as exc:
        logger.error("Database error fetching sessions for user_id=%s: %s", user_id, exc)
        raise HTTPException(status_code=500, detail="Database error fetching sessions.") from exc

    return [
        SessionSummary(
            session_id=row["session_id"],
            status=row["status"],
            created_at=row["created_at"],
            job=JobSummary(
                id=row["job_id"], 
                title=row["job_title"], 
                company_name=row["company_name"]
            ),
            resume_score=(
                (json.loads(row["enhanced_analysis"]) if isinstance(row["enhanced_analysis"], str) else row["enhanced_analysis"])["match_score"]
                if row["enhanced_analysis"] is not None
                else (
                    (json.loads(row["resume_report"]) if isinstance(row["resume_report"], str) else row["resume_report"])["score"]
                    if row["resume_report"] is not None
                    else None
                )
            ),
            enhanced_metrics=(
                json.loads(row["enhanced_analysis"]) if row["enhanced_analysis"] is not None else None
            ) if isinstance(row["enhanced_analysis"], str) else row["enhanced_analysis"],
        )
        for row in rows
    ]


# ---------------------------------------------------------------------------
# 5.3 GET /practice/session/{session_id} detail endpoint
# ---------------------------------------------------------------------------

_ACTIVE_STATUSES = {"ready_to_start", "interviewing", "completed", "interview_processing"}


async def _ensure_existing_entities(
    conn: asyncpg.Connection,
    session_id: UUID,
    enhanced_analysis: dict,
    resume_parsed_json: str,
) -> dict:
    if enhanced_analysis is None:
        enhanced_analysis = {}
    if not enhanced_analysis.get("existing_entities"):
        try:
            resume_parsed = json.loads(resume_parsed_json) if isinstance(resume_parsed_json, str) else resume_parsed_json
        except Exception:
            resume_parsed = None
            
        if resume_parsed and isinstance(resume_parsed, dict):
            entities = []
            for p in resume_parsed.get("projects", []):
                if isinstance(p, dict) and p.get("name"):
                    name = p["name"].strip()
                    if name:
                        entities.append(f"Project: {name}")
            for e in resume_parsed.get("experience", []):
                if isinstance(e, dict) and e.get("company"):
                    comp = e["company"].strip()
                    if comp:
                        entities.append(f"Company: {comp}")
            if entities:
                enhanced_analysis["existing_entities"] = entities
                # Save to database
                await conn.execute(
                    "UPDATE practice_sessions SET enhanced_analysis = $1::jsonb WHERE id = $2",
                    json.dumps(enhanced_analysis),
                    session_id,
                )
    return enhanced_analysis


@router.get("/session/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    conn: asyncpg.Connection = Depends(get_db),
) -> SessionDetailResponse:
    """Return the current state of a single practice session.

    Returns 404 when the session does not exist or belongs to a different user.
    Conditionally exposes resume_report and generated_questions based on status.
    """
    try:
        row = await conn.fetchrow(
            """
            SELECT
                ps.id                AS session_id,
                ps.status,
                ps.created_at,
                ps.resume_report,
                ps.generated_questions,
                ps.interview_assessment,
                ps.enhanced_analysis,
                ps.resume_parsed,
                ps.transcript,
                pj.id                AS job_id,
                pj.title             AS job_title,
                pj.company_name      AS company_name
            FROM practice_sessions ps
            INNER JOIN practice_jobs pj ON ps.job_id = pj.id
            WHERE ps.id = $1 AND ps.user_id = $2
            """,
            session_id,
            user_id,
        )
    except asyncpg.PostgresError as exc:
        logger.error(
            "Database error fetching session session_id=%s: %s", session_id, exc
        )
        raise HTTPException(
            status_code=500, detail="Database error fetching session."
        ) from exc

    if row is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    expose_results = row["status"] in _ACTIVE_STATUSES

    def _parse_json(val):
        if val is None:
            return None
        return json.loads(val) if isinstance(val, str) else val

    raw_questions = _parse_json(row["generated_questions"])
    # generated_questions is stored as {"questions": [...]} — unwrap to list
    if isinstance(raw_questions, dict) and "questions" in raw_questions:
        raw_questions = raw_questions["questions"]

    enhanced_analysis = _parse_json(row["enhanced_analysis"])
    if enhanced_analysis is not None:
        enhanced_analysis = await _ensure_existing_entities(
            conn,
            row["session_id"],
            enhanced_analysis,
            row["resume_parsed"]
        )

    return SessionDetailResponse(
        session_id=row["session_id"],
        status=row["status"],
        created_at=row["created_at"],
        job=JobSummary(
            id=row["job_id"], 
            title=row["job_title"], 
            company_name=row["company_name"]
        ),
        resume_report=_parse_json(row["resume_report"]) if expose_results else None,
        generated_questions=raw_questions if expose_results else None,
        interview_assessment=_parse_json(row["interview_assessment"]) if row["status"] == "completed" else None,
        enhanced_analysis=enhanced_analysis,
        transcript=_parse_json(row["transcript"]) if row["status"] == "completed" else None,
    )


@router.delete("/session/{session_id}", status_code=204)
async def delete_session(
    session_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    conn: asyncpg.Connection = Depends(get_db),
):
    """Delete a practice session and its associated job entry."""
    row = await conn.fetchrow(
        "SELECT resume_url FROM practice_sessions WHERE id = $1 AND user_id = $2",
        session_id,
        user_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Session not found.")

    # Delete from DB (cascade should handle related rows)
    await conn.execute(
        "DELETE FROM practice_sessions WHERE id = $1 AND user_id = $2",
        session_id,
        user_id,
    )

    # Best-effort cleanup of uploaded files
    try:
        file_path = row["resume_url"]
        if file_path and os.path.exists(file_path):
            session_dir = os.path.dirname(file_path)
            import shutil
            shutil.rmtree(session_dir, ignore_errors=True)
    except Exception as exc:
        logger.warning("Could not clean up session files for %s: %s", session_id, exc)


@router.get("/session/{session_id}/resume")

async def get_session_resume(
    session_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    conn: asyncpg.Connection = Depends(get_db),
):
    """Serve the original uploaded resume file."""
    row = await conn.fetchrow(
        "SELECT resume_url FROM practice_sessions WHERE id = $1 AND user_id = $2",
        session_id,
        user_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Session not found.")
        
    file_path = row["resume_url"]
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Resume file not found on server.")
        
    filename = os.path.basename(file_path)
    return FileResponse(file_path, filename=filename)

# ---------------------------------------------------------------------------
# 3.2 POST /practice/initialize endpoint
# ---------------------------------------------------------------------------

@router.post("/initialize", status_code=201, response_model=InitializeSessionResponse)
async def initialize_session(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    job_title: str = Form("Target Job Role"),
    company_name: str = Form("—"),
    jd_type: str = Form("text"),
    jd_text: Optional[str] = Form(None),
    jd_url: Optional[str] = Form(None),
    jd_file: Optional[UploadFile] = File(None),
    user_id: UUID = Depends(get_current_user_id),
    conn: asyncpg.Connection = Depends(get_db),
) -> InitializeSessionResponse:
    """Initialize a new practice session."""
    session_id = uuid4()
    job_id = uuid4()
    
    # Save resume with correct extension
    resume_ext = ".docx" if file.filename.lower().endswith(".docx") else ".pdf"
    file_path = f"{settings.STORAGE_ROOT}/{session_id}/resume{resume_ext}"

    # Extract JD text based on type
    final_jd_text = ""
    try:
        if jd_type == "url" and jd_url:
            final_jd_text = await extract_url_text(jd_url)
        elif jd_type == "file" and jd_file:
            jd_ext = ".docx" if jd_file.filename.lower().endswith(".docx") else ".pdf"
            jd_path = f"{settings.STORAGE_ROOT}/{session_id}/jd{jd_ext}"
            os.makedirs(os.path.dirname(jd_path), exist_ok=True)
            contents = await jd_file.read()
            async with aiofiles.open(jd_path, "wb") as f:
                await f.write(contents)
            final_jd_text = await extract_resume_text(jd_path)
        else:
            final_jd_text = jd_text or ""
            
        if len(final_jd_text.strip()) < 100:
            raise ValueError("Job description is too short or could not be parsed. (LinkedIn URLs are usually blocked, please copy-paste the text instead).")
    except Exception as exc:
        logger.error("Error extracting JD: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))

    # --- File I/O (must succeed before any DB writes) ---
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        contents = await file.read()
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(contents)
    except OSError as exc:
        logger.error("Filesystem error writing resume: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to save uploaded file.") from exc

    # Synchronously extract resume text to ensure it is valid
    try:
        resume_text = await extract_resume_text(file_path)
        if len(resume_text.strip()) < 50:
            raise ValueError("Resume text is empty or could not be parsed. Please upload a valid text-based PDF or DOCX.")
    except Exception as exc:
        logger.error("Error extracting Resume: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))

    # --- Database writes (single transaction) ---
    try:
        async with conn.transaction():
            await conn.execute(
                """
                INSERT INTO practice_jobs (id, user_id, title, description, company_name)
                VALUES ($1, $2, $3, $4, $5)
                """,
                job_id,
                user_id,
                job_title,
                final_jd_text,
                company_name,
            )
            await conn.execute(
                """
                INSERT INTO practice_sessions (id, user_id, job_id, resume_url, status)
                VALUES ($1, $2, $3, $4, $5)
                """,
                session_id,
                user_id,
                job_id,
                file_path,
                "parsing",
            )
    except asyncpg.PostgresError as exc:
        logger.error("Database error during session initialization: %s", exc)
        raise HTTPException(status_code=500, detail="Database error during session initialization.") from exc

    # --- Schedule background pipeline (after commit) ---
    background_tasks.add_task(
        process_session_background,
        session_id,
        job_id,
        file_path,
        request.app.state.db_pool,
        resume_text,       # pre-extracted — skip re-read in background
        final_jd_text,     # pre-extracted — skip DB round-trip in background
    )

    return InitializeSessionResponse(
        session_id=session_id,
        job_id=job_id,
        status="parsing",
        message="Practice session initialized. Async processing pipelines triggered successfully.",
    )


# ---------------------------------------------------------------------------
# 6.1 POST /practice/session/{session_id}/start endpoint
# ---------------------------------------------------------------------------

_STATUS_ERROR_MESSAGES = {
    "parsing": "Session is still processing. Please wait.",
    "scoring": "Session is still processing. Please wait.",
    "interviewing": "Session has already been started.",
    "completed": "Session has already been completed.",
}


@router.post("/session/{session_id}/start", status_code=201, response_model=StartSessionResponse)
async def start_session(
    session_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    conn: asyncpg.Connection = Depends(get_db),
) -> StartSessionResponse:
    """Provision a LiveKit room and return connection details for the interview.

    1. Fetch session + job + user data, return 404 if not found.
    2. Validate session status is ready_to_start, return 400 otherwise.
    3. Assemble RoomMetadataPayload and serialize to JSON.
    4. Provision LiveKit room, return 503 on failure.
    5. Generate access token, return 503 on failure.
    6. Update session status to 'interviewing' and store room name.
    7. Return StartSessionResponse with HTTP 201.
    """
    # --- 4.1: Fetch session row joined with practice_jobs and users ---
    try:
        row = await conn.fetchrow(
            """
            SELECT
                ps.id                   AS session_id,
                ps.user_id,
                ps.status,
                ps.generated_questions,
                ps.resume_report,
                pj.title                AS job_title,
                pj.description          AS job_description,
                u.full_name             AS candidate_name
            FROM practice_sessions ps
            INNER JOIN practice_jobs pj ON ps.job_id = pj.id
            INNER JOIN users u ON ps.user_id = u.id
            WHERE ps.id = $1 AND ps.user_id = $2
            """,
            session_id,
            user_id,
        )
    except asyncpg.PostgresError as exc:
        logger.error("Database error fetching session session_id=%s: %s", session_id, exc)
        raise HTTPException(status_code=500, detail="Database error fetching session.") from exc

    if row is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    # --- 4.2: Validate session status ---
    status = row["status"]
    if status != "ready_to_start":
        detail = _STATUS_ERROR_MESSAGES.get(status, f"Session cannot be started (status: {status}).")
        raise HTTPException(status_code=400, detail=detail)

    # --- 4.3: Assemble RoomMetadataPayload and serialize ---
    room_name = f"practice-room-{session_id}"

    def _parse_json(val):
        if val is None:
            return None
        return json.loads(val) if isinstance(val, str) else val

    generated_questions = _parse_json(row["generated_questions"]) or []
    # generated_questions is stored as {"questions": [...]} — unwrap to list
    if isinstance(generated_questions, dict) and "questions" in generated_questions:
        generated_questions = generated_questions["questions"]
    resume_report = _parse_json(row["resume_report"]) or {}

    metadata_payload = RoomMetadataPayload(
        interview_id=str(session_id),
        user_id=str(row["user_id"]),
        candidate_name=row["candidate_name"],
        job_title=row["job_title"],
        questions=generated_questions,
        resume_summary=resume_report,
        jd_summary=row["job_description"],
    )
    metadata_str = metadata_payload.model_dump_json()

    # --- 4.4: Provision room, generate token, update DB, return response ---
    try:
        await provision_room(room_name, metadata_str)
    except LiveKitProvisionError as exc:
        logger.error("LiveKit room provisioning failed for session %s: %s", session_id, exc)
        raise HTTPException(status_code=503, detail="LiveKit room provisioning failed.") from exc

    try:
        livekit_token = await generate_token(room_name, str(row["user_id"]))
    except LiveKitTokenError as exc:
        logger.error("LiveKit token generation failed for session %s: %s", session_id, exc)
        raise HTTPException(status_code=503, detail="LiveKit token generation failed.") from exc

    try:
        await conn.execute(
            """
            UPDATE practice_sessions
            SET livekit_room_name = $1, status = 'interviewing'
            WHERE id = $2
            """,
            room_name,
            session_id,
        )
    except asyncpg.PostgresError as exc:
        logger.error("Database error updating session %s: %s", session_id, exc)
        raise HTTPException(status_code=500, detail="Database error updating session.") from exc

    return StartSessionResponse(
        livekit_token=livekit_token,
        livekit_url=settings.LIVEKIT_API_URL,
        room_name=room_name,
        status="interviewing",
    )


# ---------------------------------------------------------------------------
# 9.1 POST /practice/session/complete — agent handoff webhook
# ---------------------------------------------------------------------------

@router.post("/session/complete", response_model=SessionCompleteResponse)
async def session_complete(
    payload: SessionCompletePayload,
    background_tasks: BackgroundTasks,
    conn: asyncpg.Connection = Depends(get_db),
    request: Request = None,
) -> SessionCompleteResponse:
    """Receive the session handoff from the agent worker.

    1. Look up the session by session_id; return 404 if not found.
    2. Assert status == 'interviewing'; return 409 otherwise.
    3. Atomically write transcript, end_reason, duration_seconds, status='interview_processing'.
    4. Enqueue the Phase 10 grading pipeline as a background task.
    5. Return 200 with status='received'.
    """
    session_id = payload.session_id

    # --- 1. Fetch session row ---
    try:
        row = await conn.fetchrow(
            "SELECT status FROM practice_sessions WHERE id = $1",
            session_id,
        )
    except asyncpg.PostgresError as exc:
        logger.error("DB error fetching session session_id=%s: %s", session_id, exc)
        raise HTTPException(status_code=500, detail="Database error fetching session.") from exc

    if row is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    # --- 2. Validate status ---
    if row["status"] != "interviewing":
        raise HTTPException(
            status_code=409,
            detail=f"Session is not in 'interviewing' state (current: {row['status']}).",
        )

    # --- 3. Persist transcript + metadata atomically ---
    transcript_json = json.dumps([t.model_dump() for t in payload.transcript])

    try:
        await conn.execute(
            """
            UPDATE practice_sessions
            SET transcript = $1::jsonb,
                end_reason = $2,
                duration_seconds = $3,
                status = 'interview_processing'
            WHERE id = $4
            """,
            transcript_json,
            payload.end_reason,
            payload.duration_seconds,
            session_id,
        )
    except asyncpg.PostgresError as exc:
        logger.error("DB error updating session session_id=%s: %s", session_id, exc)
        raise HTTPException(status_code=500, detail="Database error persisting session data.") from exc

    # --- 4. Enqueue Phase 10 grading pipeline ---
    db_pool = request.app.state.db_pool if request is not None else None
    background_tasks.add_task(grade_session_background, str(session_id), db_pool)

    # --- 5. Return acknowledgement ---
    return SessionCompleteResponse(status="received", session_id=session_id)


# ---------------------------------------------------------------------------
# 5.4.5 POST /practice/session/{session_id}/reanalyze_gaps endpoint
# ---------------------------------------------------------------------------

@router.post("/session/{session_id}/reanalyze_gaps", response_model=ReanalyzeGapsResponse)
async def reanalyze_gaps_endpoint(
    session_id: UUID,
    request: ReanalyzeGapsRequest,
    user_id: UUID = Depends(get_current_user_id),
    conn: asyncpg.Connection = Depends(get_db),
) -> ReanalyzeGapsResponse:
    """Re-analyze missing skills based on newly added experiences and projects."""
    try:
        row = await conn.fetchrow(
            """
            SELECT
                ps.resume_url,
                ps.enhanced_analysis,
                pj.description AS job_description
            FROM practice_sessions ps
            INNER JOIN practice_jobs pj ON ps.job_id = pj.id
            WHERE ps.id = $1 AND ps.user_id = $2
            """,
            session_id,
            user_id,
        )
    except asyncpg.PostgresError as exc:
        logger.error("DB error fetching session %s: %s", session_id, exc)
        raise HTTPException(status_code=500, detail="Database error.") from exc

    if not row:
        raise HTTPException(status_code=404, detail="Session not found.")

    try:
        from services.document_extraction import extract_resume_text
        resume_text = await extract_resume_text(row["resume_url"])
    except Exception as exc:
        logger.error("Failed to extract resume for %s: %s", session_id, exc)
        raise HTTPException(status_code=500, detail="Failed to read resume.") from exc

    def _parse_json(val):
        if val is None: return None
        import json
        return json.loads(val) if isinstance(val, str) else val

    enhanced_analysis = _parse_json(row["enhanced_analysis"]) or {}
    original_gaps = enhanced_analysis.get("gaps", [])
    
    # Convert gaps to text format with indices for LLM
    original_gaps_text = "\n".join([f"Gap {i}: {gap}" for i, gap in enumerate(original_gaps)]) if original_gaps else "None"

    from services.enhanced_analyzer import reanalyze_gaps
    try:
        remaining_gaps = await reanalyze_gaps(
            resume_text=resume_text,
            jd_text=row["job_description"],
            custom_additions=request.custom_additions,
            original_gaps_text=original_gaps_text,
        )
    except Exception as exc:
        logger.error("Failed to reanalyze gaps for %s: %s", session_id, exc)
        raise HTTPException(status_code=500, detail="Failed to reanalyze gaps.") from exc

    return ReanalyzeGapsResponse(remaining_gaps=remaining_gaps)


# ---------------------------------------------------------------------------
# 5.5 POST /practice/session/{session_id}/refine endpoint
# ---------------------------------------------------------------------------

@router.post("/session/{session_id}/refine", response_model=RefineCustomAdditionsResponse)
async def refine_custom_additions_endpoint(
    session_id: UUID,
    request: RefineCustomAdditionsRequest,
    user_id: UUID = Depends(get_current_user_id),
    conn: asyncpg.Connection = Depends(get_db),
) -> RefineCustomAdditionsResponse:
    """Refine custom additions and gap content.

    1. Fetch session data including job description and existing enhanced analysis.
    2. Call enhanced analyzer to refine custom additions and gaps.
    3. Update database with refined content.
    4. Return updated session state.
    """
    # --- 1. Fetch session row ---
    try:
        row = await conn.fetchrow(
            """
            SELECT
                ps.id                AS session_id,
                ps.status,
                ps.enhanced_analysis,
                ps.custom_additions,
                ps.resume_url,
                ps.resume_parsed,
                pj.description       AS job_description
            FROM practice_sessions ps
            INNER JOIN practice_jobs pj ON ps.job_id = pj.id
            WHERE ps.id = $1 AND ps.user_id = $2
            """,
            session_id,
            user_id,
        )
    except asyncpg.PostgresError as exc:
        logger.error(
            "Database error fetching session session_id=%s: %s", session_id, exc
        )
        raise HTTPException(
            status_code=500, detail="Database error fetching session."
        ) from exc

    if row is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    # --- 2. Parse existing data ---
    def _parse_json(val):
        if val is None:
            return None
        return json.loads(val) if isinstance(val, str) else val

    enhanced_analysis = _parse_json(row["enhanced_analysis"]) or {}
    enhanced_analysis = await _ensure_existing_entities(
        conn,
        row["session_id"],
        enhanced_analysis,
        row["resume_parsed"]
    )
    job_description = row["job_description"]

    # Extract gaps from enhanced analysis if present
    gaps_data = {}
    if enhanced_analysis.get("gaps"):
        for idx, gap_text in enumerate(enhanced_analysis["gaps"]):
            gaps_data[str(idx)] = {"gap": gap_text, "note": ""}

    # If gap_selections provided, update notes
    if request.gap_selections:
        for idx, note in request.gap_selections.items():
            if idx in gaps_data:
                gaps_data[idx]["note"] = note

    # --- 3. Refine or store directly ---
    refined_gaps_map: Dict[str, str] = {}
    refined_custom_items: List[str] = []

    if request.pre_refined:
        # Skip LLM — store provided content directly
        if request.gap_selections:
            refined_gaps_map = dict(request.gap_selections)
        if request.custom_additions.strip():
            refined_custom_items = [
                line for line in request.custom_additions.splitlines() if line.strip()
            ]
        custom_str = request.custom_additions
        refined = {
            "gaps": refined_gaps_map,
            "custom": request.custom_additions,
        }
    else:
        # Only call LLM if there is actually something to refine or optimize
        has_any_notes = any(note.strip() for note in request.gap_selections.values()) if request.gap_selections else False
        has_custom = bool(request.custom_additions.strip())
        has_opts = request.optimize_projects or request.optimize_experience or request.optimize_summary
        
        if has_any_notes or has_custom or has_opts:
            resume_text = ""
            if has_opts:
                resume_url = row.get("resume_url")
                if resume_url and os.path.exists(resume_url):
                    from services.document_extraction import extract_resume_text
                    resume_text = await extract_resume_text(resume_url)

            try:
                refined = await refine_custom_additions(
                    gaps_data=gaps_data,
                    custom_text=request.custom_additions,
                    jd_text=job_description,
                    optimize_projects=request.optimize_projects,
                    optimize_experience=request.optimize_experience,
                    optimize_summary=request.optimize_summary,
                    resume_text=resume_text,
                    targeted_answers=request.targeted_answers
                )
            except Exception as exc:
                logger.error(
                    "Failed to refine custom additions for session %s: %s", session_id, exc
                )
                raise HTTPException(
                    status_code=500, detail="Failed to refine custom additions."
                ) from exc
        else:
            refined = {"gaps": {}, "custom": ""}

        # Populate per-item return values from LLM result
        refined_gaps_map = refined.get("gaps", {})
        custom_str = refined.get("custom", "")
        refined_custom_items = [
            line for line in custom_str.splitlines() if line.strip()
        ]

    # --- 4. Update database ---
    try:
        # If selected_improvements provided, store them separately so we don't lose the original suggestions
        if request.selected_improvements is not None:
            enhanced_analysis["selected_improvements"] = request.selected_improvements

        # Update custom_additions column
        await conn.execute(
            """
            UPDATE practice_sessions
            SET custom_additions = $1
            WHERE id = $2
            """,
            request.custom_additions,
            session_id,
        )

        # Update enhanced_analysis with refined gaps
        if refined_gaps_map:
            original_gaps = enhanced_analysis.get("gaps", [])
            # Iterate through the max length of either original or refined
            max_len = max(len(original_gaps), len(refined_gaps_map) if refined_gaps_map else 0)
            refined_gaps_list = []
            for i in range(max_len):
                if str(i) in refined_gaps_map and refined_gaps_map[str(i)].strip():
                    refined_gaps_list.append(refined_gaps_map[str(i)])
                elif i < len(original_gaps):
                    refined_gaps_list.append(original_gaps[i])
                else:
                    refined_gaps_list.append("")
            enhanced_analysis["refined_gaps_list"] = refined_gaps_list
        # Update enhanced_analysis with refined custom additions
        enhanced_analysis["refined_custom_additions"] = custom_str

        await conn.execute(
            """
            UPDATE practice_sessions
            SET enhanced_analysis = $1::jsonb
            WHERE id = $2
            """,
            json.dumps(enhanced_analysis),
            session_id,
        )
    except asyncpg.PostgresError as exc:
        logger.error(
            "Database error updating session %s: %s", session_id, exc
        )
        raise HTTPException(
            status_code=500, detail="Database error updating session."
        ) from exc

    # --- 5. Return response ---
    return RefineCustomAdditionsResponse(
        session_id=session_id,
        status=row["status"],
        enhanced_analysis=enhanced_analysis,
        refined_gaps=refined_gaps_map if refined_gaps_map else None,
        refined_custom_items=refined_custom_items if refined_custom_items else None,
    )


# ---------------------------------------------------------------------------
# 6.1 GET /practice/session/{session_id}/pdf endpoint
# ---------------------------------------------------------------------------

class PDFGenerationRequest(BaseModel):
    template: Optional[str] = "Classic ATS"


@router.get("/session/{session_id}/pdf")
async def generate_pdf(
    session_id: UUID,
    template: Optional[str] = "Classic ATS",
    user_id: UUID = Depends(get_current_user_id),
    conn: asyncpg.Connection = Depends(get_db),
):
    """Generate an ATS-optimized PDF resume using enhanced analysis results.
    
    1. Fetch session data including original resume text, enhanced analysis, and custom additions.
    2. Call enhanced analyzer to generate ATS-optimized PDF.
    3. Return PDF as downloadable file.
    """
    # --- 1. Fetch session row ---
    try:
        row = await conn.fetchrow(
            """
            SELECT
                ps.id                AS session_id,
                ps.status,
                ps.resume_url,
                ps.enhanced_analysis,
                ps.custom_additions,
                pj.description       AS job_description
            FROM practice_sessions ps
            INNER JOIN practice_jobs pj ON ps.job_id = pj.id
            WHERE ps.id = $1 AND ps.user_id = $2
            """,
            session_id,
            user_id,
        )
    except asyncpg.PostgresError as exc:
        logger.error(
            "Database error fetching session session_id=%s: %s", session_id, exc
        )
        raise HTTPException(
            status_code=500, detail="Database error fetching session."
        ) from exc

    if row is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    # --- 2. Parse existing data ---
    def _parse_json(val):
        if val is None:
            return None
        return json.loads(val) if isinstance(val, str) else val

    enhanced_analysis = _parse_json(row["enhanced_analysis"]) or {}
    job_description = row["job_description"]
    
    # Extract gaps and improvements
    original_gaps = enhanced_analysis.get("gaps", [])
    refined_gaps_list = enhanced_analysis.get("refined_gaps_list")
    
    gaps_to_use = refined_gaps_list if refined_gaps_list is not None else original_gaps
    
    # Convert gaps to text format
    gaps_text = "\n".join([f"- {gap}" for gap in gaps_to_use]) if gaps_to_use else "None"

    # Convert improvements to text format
    # Use selected_improvements if they exist (meaning user went through refine flow), otherwise default to all
    improvements = enhanced_analysis.get("selected_improvements", enhanced_analysis.get("improvements", []))
    improvements_text = "\n".join([f"- {imp}" for imp in improvements]) if improvements else "None"

    # Read original resume text from file
    resume_url = row["resume_url"]
    if not resume_url or not os.path.exists(resume_url):
        raise HTTPException(status_code=404, detail="Original resume file not found.")

    try:
        from services.document_extraction import extract_resume_text
        resume_text = await extract_resume_text(resume_url)
    except Exception as exc:
        logger.error("Failed to extract text from resume file %s: %s", resume_url, exc)
        raise HTTPException(status_code=500, detail="Failed to read resume file.") from exc

    # --- 3. Call enhanced analyzer to generate PDF ---
    custom_additions = enhanced_analysis.get("refined_custom_additions", row["custom_additions"] or "")
    
    try:
        pdf_buffer = await generate_ats_pdf(
            resume_text=resume_text,
            accepted_texts=gaps_text,
            improvements_text=improvements_text,
            custom_text=custom_additions,
            jd_text=job_description,
            template_name=template,
        )
    except ImportError as exc:
        logger.error("PDF generation failed for session %s: %s", session_id, exc)
        raise HTTPException(
            status_code=500, detail="PDF generation dependencies not installed. Install with: pip install reportlab"
        ) from exc
    except Exception as exc:
        logger.error("Failed to generate PDF for session %s: %s", session_id, exc, exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to generate PDF: {exc}"
        ) from exc

    # --- 4. Return PDF as downloadable file ---
    from fastapi.responses import Response
    
    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=improved-resume-{session_id}.pdf"
        },
    )
