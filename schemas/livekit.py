from typing import Any, Dict, List
from pydantic import BaseModel, Field


class RoomMetadataPayload(BaseModel):
    """Serialized as a JSON string and injected into the LiveKit room metadata.
    Read by the AI voice agent worker to configure the interview session."""

    interview_id: str
    user_id: str
    candidate_name: str
    job_title: str
    questions: List[Dict[str, Any]]
    resume_summary: Dict[str, Any]
    jd_summary: str

    # Fixed agent configuration constants
    agent_name: str = Field(default="Aria")
    agent_voice: str = Field(default="simran")
    agent_language: str = Field(default="English")
    agent_gender: str = Field(default="F")


class StartSessionResponse(BaseModel):
    """Response returned by POST /session/{session_id}/start."""

    livekit_token: str
    livekit_url: str
    room_name: str
    status: str
