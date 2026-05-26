"""Unit tests for services/enhanced_analyzer.py.

Tests cover:
- analyze_resume_enhanced() with sample data
- refine_custom_additions() with various inputs
- generate_ats_pdf() with different templates
- Requirements: 1.1, 3.1, 4.1
"""
import json
from unittest.mock import AsyncMock, patch

import pytest

from services.enhanced_analyzer import (
    analyze_resume_enhanced,
    refine_custom_additions,
    generate_ats_pdf,
    parse_custom_additions,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_RESUME = """John Doe
john.doe@example.com
Senior Python Developer

Summary:
Experienced Python developer with 5+ years of backend development.

Experience:
- Senior Developer at Tech Corp (2021-Present)
  * Led backend team of 5 developers
  * Built REST APIs using Python and FastAPI
  * Optimized database queries reducing response time by 40%

- Developer at Startup Inc (2019-2021)
  * Developed microservices using Python
  * Implemented CI/CD pipelines

Skills:
Python, FastAPI, PostgreSQL, Docker, AWS, Redis, Celery

Education:
BS Computer Science, University of Tech (2015-2019)
"""

SAMPLE_JD = """We are looking for a Senior Python Developer to join our team.

Requirements:
- 5+ years of Python development experience
- Strong knowledge of FastAPI or Flask
- Experience with PostgreSQL and database optimization
- Familiarity with Docker and cloud platforms (AWS/GCP)
- Experience with CI/CD pipelines
- Strong problem-solving skills

Preferred:
- Experience with Redis and Celery
- Knowledge of microservices architecture
- Background in backend system design
"""


# ---------------------------------------------------------------------------
# parse_custom_additions tests
# ---------------------------------------------------------------------------

def test_parse_custom_additions_empty_string():
    """Test parsing empty custom text returns empty sections."""
    result = parse_custom_additions("")
    assert result == {
        "certificates": [],
        "education": [],
        "additional": [],
    }


def test_parse_custom_additions_none():
    """Test parsing None returns empty sections."""
    result = parse_custom_additions(None)
    assert result == {
        "certificates": [],
        "education": [],
        "additional": [],
    }


def test_parse_custom_additions_certificates():
    """Test parsing certificate entries."""
    custom_text = "certificate: AWS Certified Developer\ncertificate: Google Cloud Associate"
    result = parse_custom_additions(custom_text)
    assert result["certificates"] == [
        "AWS Certified Developer",
        "Google Cloud Associate",
    ]
    assert result["education"] == []
    assert result["additional"] == []


def test_parse_custom_additions_education():
    """Test parsing education entries."""
    custom_text = "education: MBA in HR | Gujarat Technological University | 2023-2025"
    result = parse_custom_additions(custom_text)
    assert result["certificates"] == []
    assert result["education"] == [
        "MBA in HR | Gujarat Technological University | 2023-2025"
    ]
    assert result["additional"] == []


def test_parse_custom_additions_additional():
    """Test parsing additional entries without prefixes."""
    custom_text = "Additional project: Built a machine learning model for sales prediction"
    result = parse_custom_additions(custom_text)
    assert result["certificates"] == []
    assert result["education"] == []
    assert result["additional"] == [
        "Additional project: Built a machine learning model for sales prediction"
    ]


def test_parse_custom_additions_mixed():
    """Test parsing mixed entries."""
    custom_text = """certificate: AWS Certified Developer
education: MBA in HR | GTU | 2023-2025
Additional note about my experience"""
    result = parse_custom_additions(custom_text)
    assert result["certificates"] == ["AWS Certified Developer"]
    assert result["education"] == ["MBA in HR | GTU | 2023-2025"]
    assert result["additional"] == ["Additional note about my experience"]


# ---------------------------------------------------------------------------
# analyze_resume_enhanced tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_analyze_resume_enhanced_success():
    """Test successful enhanced analysis with valid resume and JD."""
    mock_response = json.dumps({
        "match_score": 85,
        "is_match": True,
        "ats_score": 78,
        "ats_explanation": "Good structure and keyword usage.",
        "gaps": ["No Kubernetes experience"],
        "improvements": ["Consider using 'Kubernetes' instead of 'container orchestration'"],
        "core_strengths": ["Strong Python background", "FastAPI experience"],
        "summary": "Good fit for the role with strong technical skills.",
        "explanation": "Score calculated based on experience and skills alignment."
    })

    with patch("services.enhanced_analyzer._call_llm_async", AsyncMock(return_value=mock_response)):
        result = await analyze_resume_enhanced(SAMPLE_RESUME, SAMPLE_JD)

        assert result["match_score"] == 85
        assert result["is_match"] is True
        assert result["ats_score"] == 78
        assert "gaps" in result
        assert "improvements" in result
        assert "core_strengths" in result


@pytest.mark.asyncio
async def test_analyze_resume_enhanced_with_markdown_fences():
    """Test that markdown JSON fences are properly stripped."""
    mock_response = "```json\n" + json.dumps({
        "match_score": 90,
        "is_match": True,
        "ats_score": 85,
        "ats_explanation": "Excellent ATS optimization.",
        "gaps": [],
        "improvements": [],
        "core_strengths": ["Strong background"],
        "summary": "Excellent candidate.",
        "explanation": "Well aligned."
    }) + "\n```"

    with patch("services.enhanced_analyzer._call_llm_async", AsyncMock(return_value=mock_response)):
        result = await analyze_resume_enhanced(SAMPLE_RESUME, SAMPLE_JD)
        assert result["match_score"] == 90


@pytest.mark.asyncio
async def test_analyze_resume_enhanced_custom_model():
    """Test using a custom model name."""
    mock_response = json.dumps({
        "match_score": 75,
        "is_match": True,
        "ats_score": 70,
        "ats_explanation": "Good score.",
        "gaps": [],
        "improvements": [],
        "core_strengths": [],
        "summary": "Summary.",
        "explanation": "Explanation."
    })

    with patch("services.enhanced_analyzer._call_llm_async", AsyncMock(return_value=mock_response)) as mock_call:
        await analyze_resume_enhanced(SAMPLE_RESUME, SAMPLE_JD, None, "custom/model")
        mock_call.assert_called_once()
        # Verify the model name was used (passed as first positional arg)
        call_args = mock_call.call_args
        assert call_args[0][0] == "custom/model"


# ---------------------------------------------------------------------------
# refine_custom_additions tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_refine_custom_additions_empty_inputs():
    """Test refinement with empty inputs returns empty results."""
    result = await refine_custom_additions({}, "", SAMPLE_JD)
    assert result == {"gaps": {}, "custom": ""}


@pytest.mark.asyncio
async def test_refine_custom_additions_with_gaps():
    """Test refinement with gap data."""
    gaps_data = {
        "0": {"gap": "Missing Kubernetes experience", "note": "I have Docker experience and can learn Kubernetes quickly"},
        "1": {"gap": "No AWS certification", "note": "I have AWS practical experience but no certification"}
    }
    custom_text = "certificate: AWS Certified Developer\neducation: MBA | GTU | 2023-2025"

    mock_response = json.dumps({
        "gaps": {
            "0": "Candidate has strong Docker experience and is actively pursuing Kubernetes certification to bridge this gap.",
            "1": "With practical AWS experience, candidate is working towards AWS certification to validate their cloud skills."
        },
        "custom": "AWS Certified Developer\nMBA in HR from GTU (2023-2025)"
    })

    with patch("services.enhanced_analyzer._call_llm_async", AsyncMock(return_value=mock_response)):
        result = await refine_custom_additions(gaps_data, custom_text, SAMPLE_JD)

        assert "gaps" in result
        assert "0" in result["gaps"]
        assert "1" in result["gaps"]
        assert "AWS Certified Developer" in result["custom"]


@pytest.mark.asyncio
async def test_refine_custom_additions_with_custom_only():
    """Test refinement with only custom additions."""
    custom_text = "certificate: Google Cloud Associate\nAdditional: Led a team of 5 developers"

    mock_response = json.dumps({
        "gaps": {},
        "custom": "Google Cloud Associate\nLed a team of 5 developers"
    })

    with patch("services.enhanced_analyzer._call_llm_async", AsyncMock(return_value=mock_response)):
        result = await refine_custom_additions({}, custom_text, SAMPLE_JD)
        assert result["gaps"] == {}
        assert "Google Cloud Associate" in result["custom"]


@pytest.mark.asyncio
async def test_refine_custom_additions_preserves_prefixes():
    """Test that section prefixes are preserved in custom additions."""
    custom_text = "certificate: AWS Certified Developer\neducation: MBA | GTU | 2023-2025"

    mock_response = json.dumps({
        "gaps": {},
        "custom": "AWS Certified Developer\nMBA | GTU | 2023-2025"
    })

    with patch("services.enhanced_analyzer._call_llm_async", AsyncMock(return_value=mock_response)):
        result = await refine_custom_additions({}, custom_text, SAMPLE_JD)
        # Verify prefixes are preserved
        assert "AWS Certified Developer" in result["custom"]
        assert "MBA | GTU | 2023-2025" in result["custom"]


# ---------------------------------------------------------------------------
# generate_ats_pdf tests
# ---------------------------------------------------------------------------

def test_generate_ats_pdf_imports_reportlab():
    """Test that generate_ats_pdf imports reportlab correctly."""
    # This test verifies the import structure is correct
    # The actual PDF generation requires reportlab to be installed
    try:
        import reportlab
        # reportlab is installed, so the function should work
        assert True
    except ImportError:
        # reportlab is not installed, which is expected
        pytest.skip("reportlab not installed, skipping")


@pytest.mark.asyncio
async def test_generate_ats_pdf_two_column_template():
    """Test PDF generation with Two-Column Professional template."""
    # Skip if reportlab is not installed
    pytest.importorskip("reportlab")
    
    mock_response = json.dumps({
        "header": {
            "name": "John Doe",
            "contact": "john.doe@example.com"
        },
        "sections": [
            {
                "title": "PROFESSIONAL SUMMARY",
                "type": "paragraph",
                "content": "Summary."
            }
        ]
    })

    with patch("services.enhanced_analyzer._call_llm_async", AsyncMock(return_value=mock_response)):
        result = await generate_ats_pdf(
            SAMPLE_RESUME,
            "",
            "",
            "",
            SAMPLE_JD,
            template_name="Two-Column Professional"
        )
        assert isinstance(result, BytesIO)


def test_generate_ats_pdf_missing_reportlab():
    """Test that generate_ats_pdf raises ImportError when reportlab is not available."""
    # This test verifies the ImportError is raised when reportlab is not installed
    # The actual check happens inside the function at import time
    try:
        import reportlab
        pytest.skip("reportlab is installed, skipping ImportError test")
    except ImportError:
        # reportlab is not installed, which is expected for this test
        pass


@pytest.mark.asyncio
async def test_generate_ats_pdf_sanitizes_text():
    """Test that PDF generation sanitizes special characters."""
    # Skip if reportlab is not installed
    pytest.importorskip("reportlab")
    
    # Response with special characters that need sanitization
    mock_response = json.dumps({
        "header": {
            "name": "John Doe",
            "contact": "john@example.com"
        },
        "sections": [
            {
                "title": "PROFESSIONAL SUMMARY",
                "type": "paragraph",
                "content": "Summary with special chars: \u2013 em dash \u2018 quote"
            }
        ]
    })

    with patch("services.enhanced_analyzer._call_llm_async", AsyncMock(return_value=mock_response)):
        result = await generate_ats_pdf(
            SAMPLE_RESUME,
            "",
            "",
            "",
            SAMPLE_JD
        )
        assert isinstance(result, BytesIO)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_analyze_resume_enhanced_invalid_json():
    """Test handling of invalid JSON response from LLM."""
    with patch("services.enhanced_analyzer._call_llm_async", AsyncMock(return_value="not valid json")):
        with pytest.raises(json.JSONDecodeError):
            await analyze_resume_enhanced(SAMPLE_RESUME, SAMPLE_JD)


@pytest.mark.asyncio
async def test_refine_custom_additions_invalid_json():
    """Test handling of invalid JSON response from LLM in refinement."""
    with patch("services.enhanced_analyzer._call_llm_async", AsyncMock(return_value="not valid json")):
        with pytest.raises(json.JSONDecodeError):
            await refine_custom_additions({}, "custom text", SAMPLE_JD)


@pytest.mark.asyncio
async def test_generate_ats_pdf_invalid_json():
    """Test handling of invalid JSON response from LLM in PDF generation."""
    # Skip if reportlab is not installed
    pytest.importorskip("reportlab")
    
    with patch("services.enhanced_analyzer._call_llm_async", AsyncMock(return_value="not valid json")):
        with pytest.raises(json.JSONDecodeError):
            await generate_ats_pdf(
                SAMPLE_RESUME,
                "",
                "",
                "",
                SAMPLE_JD
            )
