"""Unit tests for Phase 10 grading pipeline.

Covers:
- count_candidate_turns helper
- map_verdict helper
- completion ratio math (4-of-8 scenario)
- grade_session_background happy path
- grade_session_background LLM validation failure
- grade_session_background session not found

Requirements: 2.5, 1.3, 3.5, 6.3
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.background_pipeline import (
    count_candidate_turns,
    map_verdict,
    grade_session_background,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_turn(speaker: str, text: str) -> dict:
    return {"speaker": speaker, "text": text, "created_at": "2024-01-01T00:00:00Z"}


def _make_valid_assessment_json(
    technical: int = 80,
    role_alignment: int = 80,
    communication: int = 80,
    presence: int = 80,
) -> str:
    return json.dumps({
        "overall_score": 0,
        "practice_verdict": "",
        "summary": "Good interview.",
        "dimension_scores": {
            "technical": {
                "score": technical, "max_score": 100, "label": "Technical Familiarity",
                "verdict": "Good", "evidence": "Discussed Python.", "strengths": [], "gaps": [],
            },
            "role_alignment": {
                "score": role_alignment, "max_score": 100, "label": "Role Alignment",
                "verdict": "Good", "evidence": "Fits the role.", "strengths": [], "gaps": [],
            },
            "communication": {
                "score": communication, "max_score": 100, "label": "Communication Skills",
                "verdict": "Good", "evidence": "Clear answers.", "strengths": [], "gaps": [],
            },
            "presence": {
                "score": presence, "max_score": 100, "label": "Presence & Engagement",
                "verdict": "Good", "evidence": "Engaged.", "strengths": [], "gaps": [],
            },
        },
        "overall_strengths": ["Python"],
        "overall_gaps": [],
        "technical_round_probes": ["Probe 1", "Probe 2", "Probe 3"],
        "turns_analyzed": 10,
        "completion_ratio": 0.0,
    })


def _make_db_pool(session_row=None, job_row=None):
    """Build a minimal asyncpg pool mock."""
    conn = AsyncMock()

    async def _fetchrow(query, *args):
        if "practice_sessions" in query:
            return session_row
        if "practice_jobs" in query:
            return job_row
        return None

    conn.fetchrow = AsyncMock(side_effect=_fetchrow)
    conn.execute = AsyncMock()

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    return pool, conn


# ---------------------------------------------------------------------------
# count_candidate_turns
# ---------------------------------------------------------------------------

def test_count_candidate_turns_mixed():
    """Counts only candidate turns with non-empty text."""
    transcript = [
        _make_turn("agent", "Tell me about yourself."),
        _make_turn("candidate", "I am a Python developer."),
        _make_turn("agent", "What about your projects?"),
        _make_turn("candidate", "I built a REST API."),
        _make_turn("candidate", ""),          # empty — should not count
        _make_turn("candidate", "   "),       # whitespace only — should not count
    ]
    assert count_candidate_turns(transcript) == 2


def test_count_candidate_turns_agent_only():
    """Returns 0 when there are no candidate turns."""
    transcript = [
        _make_turn("agent", "Hello."),
        _make_turn("agent", "Goodbye."),
    ]
    assert count_candidate_turns(transcript) == 0


def test_count_candidate_turns_empty_transcript():
    """Returns 0 for an empty transcript."""
    assert count_candidate_turns([]) == 0


# ---------------------------------------------------------------------------
# map_verdict
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("score,expected", [
    (80, "High Alignment"),
    (100, "High Alignment"),
    (79, "Strong Alignment"),
    (68, "Strong Alignment"),
    (67, "Moderate Alignment"),
    (52, "Moderate Alignment"),
    (51, "Emerging Alignment"),
    (0, "Emerging Alignment"),
])
def test_map_verdict_thresholds(score, expected):
    assert map_verdict(score) == expected


# ---------------------------------------------------------------------------
# Completion ratio math — 4-of-8 scenario
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_grade_session_completion_ratio_half():
    """4 candidate turns out of 8 expected → completion_ratio=0.5, final_score halved.

    Requirements: 2.5
    """
    # 4 substantive candidate turns
    transcript = (
        [_make_turn("agent", f"Q{i}") for i in range(4)]
        + [_make_turn("candidate", f"Answer {i}") for i in range(4)]
    )

    # All dimension scores = 80 → weighted_raw = 80
    # final_score = round(80 * 0.5) = 40
    assessment_json = _make_valid_assessment_json(80, 80, 80, 80)

    session_row = {
        "transcript": json.dumps(transcript),
        "resume_parsed": json.dumps({"skills": []}),
        "job_id": "job-1",
    }
    job_row = {"description": "Senior Python Engineer"}

    pool, conn = _make_db_pool(session_row=session_row, job_row=job_row)

    with patch("services.background_pipeline.call_openrouter", AsyncMock(return_value=assessment_json)):
        await grade_session_background("session-1", pool)

    # Verify DB was called with completed status
    conn.execute.assert_called_once()
    call_args = conn.execute.call_args
    sql = call_args[0][0]
    assert "status='completed'" in sql

    # Verify the persisted assessment has the correct computed values
    persisted_json = call_args[0][1]
    persisted = json.loads(persisted_json)
    assert persisted["completion_ratio"] == 0.5
    assert persisted["overall_score"] == round(80 * 0.5)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_grade_session_happy_path():
    """Full pipeline: valid DB rows + valid LLM response → DB UPDATE with status='completed'.

    Requirements: 6.3
    """
    transcript = [
        _make_turn("agent", "Tell me about yourself."),
        _make_turn("candidate", "I am a Python developer with 5 years of experience."),
        _make_turn("agent", "What projects have you built?"),
        _make_turn("candidate", "I built a microservices platform."),
    ]
    assessment_json = _make_valid_assessment_json()

    session_row = {
        "transcript": json.dumps(transcript),
        "resume_parsed": json.dumps({"skills": ["Python"]}),
        "job_id": "job-42",
    }
    job_row = {"description": "Backend Engineer role"}

    pool, conn = _make_db_pool(session_row=session_row, job_row=job_row)

    with patch("services.background_pipeline.call_openrouter", AsyncMock(return_value=assessment_json)):
        await grade_session_background("session-42", pool)

    conn.execute.assert_called_once()
    sql = conn.execute.call_args[0][0]
    assert "status='completed'" in sql
    assert "interview_assessment" in sql


# ---------------------------------------------------------------------------
# LLM validation failure
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_grade_session_llm_validation_failure():
    """Malformed LLM JSON → DB UPDATE must NOT be called.

    Requirements: 3.5
    """
    transcript = [_make_turn("candidate", "Some answer.")]
    session_row = {
        "transcript": json.dumps(transcript),
        "resume_parsed": json.dumps({}),
        "job_id": "job-1",
    }
    job_row = {"description": "Some JD"}

    pool, conn = _make_db_pool(session_row=session_row, job_row=job_row)

    malformed_json = json.dumps({"not_a_valid_assessment": True})

    with patch("services.background_pipeline.call_openrouter", AsyncMock(return_value=malformed_json)):
        await grade_session_background("session-bad", pool)

    conn.execute.assert_not_called()


# ---------------------------------------------------------------------------
# Session not found
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_grade_session_not_found_no_exception():
    """DB returns None for session row → function returns without raising.

    Requirements: 1.3
    """
    pool, conn = _make_db_pool(session_row=None, job_row=None)

    # Should not raise
    await grade_session_background("session-missing", pool)

    conn.execute.assert_not_called()
