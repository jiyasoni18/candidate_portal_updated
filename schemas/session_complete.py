from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class TranscriptTurn(BaseModel):
    speaker: Literal["agent", "candidate"]
    text: str = Field(..., min_length=1)
    created_at: float
    recovered: bool = False


class SessionCompletePayload(BaseModel):
    session_id: UUID
    end_reason: Literal["normal", "silence_timeout", "disciplinary", "candidate_leave"]
    duration_seconds: int = Field(..., ge=0)
    transcript: list[TranscriptTurn] = Field(..., min_length=1)


class SessionCompleteResponse(BaseModel):
    status: str
    session_id: UUID
