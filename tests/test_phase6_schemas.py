"""Unit tests for schemas/livekit.py — RoomMetadataPayload serialization.

Requirements: 2.1, 2.5
"""
import json

from schemas.livekit import RoomMetadataPayload, StartSessionResponse


SAMPLE_QUESTIONS = [
    {
        "id": 1,
        "question": "Tell me about yourself.",
        "category": "opening",
        "expected_duration_seconds": 120,
    }
]

SAMPLE_RESUME_SUMMARY = {
    "score": 85,
    "reference_to_jd": "Strong match",
    "strengths": ["Python", "FastAPI"],
    "weaknesses": ["No cloud experience"],
}


def _make_payload(**overrides) -> RoomMetadataPayload:
    defaults = dict(
        interview_id="session-123",
        user_id="user-456",
        candidate_name="Jane Doe",
        job_title="Backend Engineer",
        questions=SAMPLE_QUESTIONS,
        resume_summary=SAMPLE_RESUME_SUMMARY,
        jd_summary="Seeking a Python/FastAPI engineer.",
    )
    defaults.update(overrides)
    return RoomMetadataPayload(**defaults)


def test_agent_constants_are_defaults():
    """Agent fields default to the fixed blueprint constants."""
    payload = _make_payload()
    assert payload.agent_name == "Aria"
    assert payload.agent_voice == "simran"
    assert payload.agent_language == "English"
    assert payload.agent_gender == "F"


def test_serialized_json_contains_all_required_fields():
    """Serialized JSON must include every agent blueprint field (Requirement 2.1)."""
    payload = _make_payload()
    data = json.loads(payload.model_dump_json())

    required_keys = {
        "interview_id", "user_id", "candidate_name", "job_title",
        "questions", "resume_summary", "jd_summary",
        "agent_name", "agent_voice", "agent_language", "agent_gender",
    }
    assert required_keys.issubset(data.keys())


def test_serialized_values_match_inputs():
    """Serialized output values must match the inputs provided (Requirement 2.5)."""
    payload = _make_payload()
    data = json.loads(payload.model_dump_json())

    assert data["interview_id"] == "session-123"
    assert data["user_id"] == "user-456"
    assert data["candidate_name"] == "Jane Doe"
    assert data["job_title"] == "Backend Engineer"
    assert data["jd_summary"] == "Seeking a Python/FastAPI engineer."
    assert data["questions"] == SAMPLE_QUESTIONS
    assert data["resume_summary"] == SAMPLE_RESUME_SUMMARY


def test_agent_constants_can_be_overridden():
    """Agent fields can be overridden when needed."""
    payload = _make_payload(agent_name="Bob", agent_voice="custom", agent_gender="M")
    assert payload.agent_name == "Bob"
    assert payload.agent_voice == "custom"
    assert payload.agent_gender == "M"


def test_start_session_response_serialization():
    """StartSessionResponse serializes all connection detail fields."""
    resp = StartSessionResponse(
        livekit_token="jwt.token.here",
        livekit_url="ws://localhost:7880",
        room_name="practice-room-session-123",
        status="interviewing",
    )
    data = json.loads(resp.model_dump_json())
    assert data["livekit_token"] == "jwt.token.here"
    assert data["livekit_url"] == "ws://localhost:7880"
    assert data["room_name"] == "practice-room-session-123"
    assert data["status"] == "interviewing"
