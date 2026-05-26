"""Unit tests for services/background_pipeline.py pipeline stages.

Tests cover:
- extract_resume_text truncation at 25,000 characters
- run_pipeline_1 raises on API failure and schema validation failure
- run_pipeline_2 raises on missing resume_report or questions keys
- process_session_background terminates cleanly on any stage failure

Requirements: 1.4, 2.2, 3.4, 3.5, 4.6, 4.7
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from services.background_pipeline import (
    extract_resume_text,
    run_pipeline_1,
    run_pipeline_2,
    process_session_background,
)
from schemas.resume import ResumeParsedData, ResumeReportData
from schemas.questions import QuestionArraySchema


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_RESUME_JSON = json.dumps({
    "personal_info": {"name": "Jane Doe", "email": None, "phone": None,
                      "linkedin": None, "github": None, "portfolio": None},
    "summary": "Python engineer",
    "skills": ["Python"],
    "experience": [],
    "projects": [],
    "education": [],
    "certifications": [],
})

VALID_PIPELINE_2_JSON = json.dumps({
    "resume_report": {
        "score": 75,
        "reference_to_jd": "Good alignment.",
        "strengths": ["Python"],
        "weaknesses": ["No CI/CD"],
    },
    "questions": [
        {"id": i, "question": f"Question {i}?", "category": cat, "expected_duration_seconds": 120}
        for i, cat in enumerate(
            ["opening", "experience", "experience", "rolefit", "situational",
             "rolefit", "behavioral", "closing"], start=1
        )
    ],
})


# ---------------------------------------------------------------------------
# extract_resume_text — truncation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extract_resume_text_truncates_at_25000_chars(tmp_path):
    """Requirement 2.2: output is capped at 25,000 characters."""
    import fitz

    # Create a PDF with enough text to exceed 25,000 chars
    long_text = "A" * 30_000
    pdf_path = tmp_path / "resume.pdf"

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), long_text[:3000])  # fitz limits per insert; use multiple
    # Insert text across multiple pages to accumulate enough characters
    for _ in range(10):
        p = doc.new_page()
        p.insert_text((50, 50), "B" * 3000)
    doc.save(str(pdf_path))
    doc.close()

    result = await extract_resume_text(str(pdf_path))
    assert len(result) <= 25_000


# ---------------------------------------------------------------------------
# run_pipeline_1 — error cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_pipeline_1_raises_on_api_failure():
    """Requirement 3.4: run_pipeline_1 propagates httpx errors from call_openrouter."""
    with patch(
        "services.background_pipeline.call_openrouter",
        AsyncMock(side_effect=httpx.RequestError("connection refused")),
    ):
        with pytest.raises(httpx.RequestError):
            await run_pipeline_1("some resume text")


@pytest.mark.asyncio
async def test_run_pipeline_1_raises_on_schema_validation_failure():
    """Requirement 3.5: run_pipeline_1 raises when LLM returns JSON that fails ResumeParsedData validation."""
    bad_json = json.dumps({"unexpected_key": "value"})
    with patch(
        "services.background_pipeline.call_openrouter",
        AsyncMock(return_value=bad_json),
    ):
        with pytest.raises(Exception):
            await run_pipeline_1("some resume text")


# ---------------------------------------------------------------------------
# run_pipeline_2 — missing keys
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_pipeline_2_raises_on_missing_resume_report_key():
    """Requirement 4.6: run_pipeline_2 raises when resume_report key is absent."""
    bad_json = json.dumps({"questions": []})
    with patch(
        "services.background_pipeline.call_openrouter",
        AsyncMock(return_value=bad_json),
    ):
        parsed = ResumeParsedData.model_validate_json(VALID_RESUME_JSON)
        with pytest.raises(KeyError):
            await run_pipeline_2(parsed, "some jd text")


@pytest.mark.asyncio
async def test_run_pipeline_2_raises_on_missing_questions_key():
    """Requirement 4.7: run_pipeline_2 raises when questions key is absent."""
    bad_json = json.dumps({
        "resume_report": {
            "score": 50,
            "reference_to_jd": "ok",
            "strengths": [],
            "weaknesses": [],
        }
    })
    with patch(
        "services.background_pipeline.call_openrouter",
        AsyncMock(return_value=bad_json),
    ):
        parsed = ResumeParsedData.model_validate_json(VALID_RESUME_JSON)
        with pytest.raises(KeyError):
            await run_pipeline_2(parsed, "some jd text")


# ---------------------------------------------------------------------------
# process_session_background — clean termination on failure
# ---------------------------------------------------------------------------

def _make_db_pool_mock():
    """Return a minimal asyncpg pool mock that supports async context manager acquire()."""
    conn = AsyncMock()
    conn.execute = AsyncMock()
    conn.fetchrow = AsyncMock(return_value={"description": "some jd text"})

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    return pool


@pytest.mark.asyncio
async def test_process_session_background_does_not_raise_on_extraction_failure():
    """Requirement 1.4: pipeline swallows exceptions and never propagates them."""
    with patch(
        "services.background_pipeline.extract_resume_text",
        AsyncMock(side_effect=FileNotFoundError("no file")),
    ):
        # Should complete without raising
        await process_session_background("sid", "jid", "/no/file.pdf", _make_db_pool_mock())


@pytest.mark.asyncio
async def test_process_session_background_does_not_raise_on_pipeline1_failure():
    """Requirement 1.4: pipeline swallows Pipeline 1 API errors."""
    with patch(
        "services.background_pipeline.extract_resume_text",
        AsyncMock(return_value="resume text"),
    ), patch(
        "services.background_pipeline.call_openrouter",
        AsyncMock(side_effect=httpx.RequestError("timeout")),
    ):
        await process_session_background("sid", "jid", "/no/file.pdf", _make_db_pool_mock())


@pytest.mark.asyncio
async def test_process_session_background_does_not_raise_on_pipeline2_failure():
    """Requirement 1.4: pipeline swallows Pipeline 2 validation errors."""
    call_count = 0

    async def _mock_call(system_prompt, user_content):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return VALID_RESUME_JSON
        # Pipeline 2 returns invalid data
        return json.dumps({"bad": "data"})

    with patch(
        "services.background_pipeline.extract_resume_text",
        AsyncMock(return_value="resume text"),
    ), patch(
        "services.background_pipeline.call_openrouter",
        AsyncMock(side_effect=_mock_call),
    ):
        await process_session_background("sid", "jid", "/no/file.pdf", _make_db_pool_mock())
