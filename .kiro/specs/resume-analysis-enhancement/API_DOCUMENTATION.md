# Resume Analysis Enhancement - API Documentation

## Overview

This document describes the new API endpoints and enhanced analysis features added to the practice session workflow. These enhancements provide candidates with detailed ATS-friendly resume analysis, gap identification, improvement suggestions, and the ability to generate improved PDF resumes.

## New Endpoints

### 1. Refine Custom Additions

**Endpoint:** `POST /practice/session/{session_id}/refine`

**Description:** Submit custom additions and gap selections to refine the enhanced analysis content.

**Request Body:**
```json
{
  "custom_additions": "Certifications: AWS Certified Developer\nEducation: MBA in Human Resources | Gujarat Technological University | 2023 - 2025 | 8.5 CGPA\nAdditional: Strong leadership skills demonstrated through volunteer work",
  "gap_selections": {
    "0": "I have worked with React and TypeScript in my academic projects",
    "1": "I have experience with cloud platforms through university projects"
  }
}
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ready_to_start",
  "enhanced_analysis": {
    "match_score": 85,
    "ats_score": 78,
    "ats_explanation": "Resume structure is clean but could benefit from more JD-aligned keywords",
    "gaps": [
      "Missing direct experience with React and TypeScript in professional settings",
      "Limited exposure to production-level cloud deployment scenarios"
    ],
    "improvements": [
      "Consider using 'React' instead of 'JavaScript Frameworks' to match JD terminology",
      "Replace 'AWS services' with 'AWS EC2, S3, Lambda' as specified in JD"
    ],
    "core_strengths": [
      "Strong academic foundation in full-stack development",
      "Proven ability to deliver complete projects with measurable impact"
    ],
    "summary": "Candidate shows strong potential with relevant academic experience. Focus on aligning terminology with JD requirements and providing more context about cloud exposure.",
    "explanation": "Score calculated based on 2 years of relevant experience (internships counted), 40/45 technical skills match, and 25/30 project alignment."
  }
}
```

**Error Responses:**
- `404 Not Found`: Session not found or belongs to different user
- `500 Internal Server Error`: Failed to refine custom additions

---

### 2. Generate PDF

**Endpoint:** `GET /practice/session/{session_id}/pdf`

**Description:** Generate an ATS-optimized PDF resume using enhanced analysis results and custom additions.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| template | string | "Classic ATS" | PDF template to use. Options: "Classic ATS", "Modern Accent", "Two-Column Professional" |

**Response:**
- **Content-Type:** `application/pdf`
- **Content-Disposition:** `attachment; filename=improved-resume-{session_id}.pdf`

**Example Request:**
```
GET /practice/session/550e8400-e29b-41d4-a716-446655440000/pdf?template=Modern%20Accent
```

**Error Responses:**
- `404 Not Found`: Session not found or original resume file missing
- `500 Internal Server Error`: PDF generation failed (dependencies not installed or processing error)

---

## Updated Endpoints

### Get Session Detail

**Endpoint:** `GET /practice/session/{session_id}`

**Description:** Returns the current state of a practice session, now including enhanced analysis data.

**Response (with enhanced analysis):**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ready_to_start",
  "created_at": "2024-01-15T10:30:00Z",
  "job": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "title": "Senior Software Engineer"
  },
  "resume_report": {
    "score": 78,
    "reference_to_jd": "Strong alignment with core requirements",
    "strengths": ["5+ years Python experience", "AWS certification"],
    "weaknesses": ["Limited Kubernetes exposure"]
  },
  "generated_questions": [
    {
      "id": "q1",
      "question": "Tell me about a time you used Python to solve a complex problem...",
      "category": "technical"
    }
  ],
  "interview_assessment": null,
  "enhanced_analysis": {
    "match_score": 85,
    "ats_score": 78,
    "ats_explanation": "Resume structure is clean but could benefit from more JD-aligned keywords",
    "gaps": [
      "Missing direct experience with React and TypeScript in professional settings"
    ],
    "improvements": [
      "Consider using 'React' instead of 'JavaScript Frameworks' to match JD terminology"
    ],
    "core_strengths": [
      "Strong academic foundation in full-stack development"
    ],
    "summary": "Candidate shows strong potential with relevant academic experience.",
    "explanation": "Score calculated based on 2 years of relevant experience..."
  }
}
```

**Response (without enhanced analysis - backward compatible):**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ready_to_start",
  "created_at": "2024-01-15T10:30:00Z",
  "job": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "title": "Senior Software Engineer"
  },
  "resume_report": {
    "score": 78,
    "reference_to_jd": "Strong alignment with core requirements",
    "strengths": ["5+ years Python experience", "AWS certification"],
    "weaknesses": ["Limited Kubernetes exposure"]
  },
  "generated_questions": [...],
  "interview_assessment": null,
  "enhanced_analysis": null
}
```

---

## Enhanced Analysis Output Format

### Data Structure

The `enhanced_analysis` field contains the following structured data:

| Field | Type | Description |
|-------|------|-------------|
| `match_score` | integer (0-100) | Overall fit score between candidate and job description |
| `ats_score` | integer (0-100) | ATS-friendliness score of the original resume |
| `ats_explanation` | string | Explanation of the ATS score |
| `gaps` | array of strings | Missing skills/requirements explicitly mentioned in JD |
| `improvements` | array of strings | Terminology suggestions to align with JD keywords |
| `core_strengths` | array of strings | Candidate's standout qualifications |
| `summary` | string | 2-3 sentence high-level summary |
| `explanation` | string | Detailed explanation of score calculation |

### Scoring Guidelines

#### Match Score (0-100)
- **Years of Experience:** Up to 15 points (or 10 if no experience required)
- **Core Technical Skills:** Up to 45 points
- **Projects and Practical Depth:** Up to 30 points
- **Soft-skills and Domain Knowledge:** Up to 10 points

#### ATS Score (0-100)
Based on:
- Resume structure and formatting
- Keyword optimization
- Section organization
- Readability for parsing systems

### Gap Detection Rules

1. **Only explicit gaps:** Only list gaps for skills/requirements EXPLICITLY mentioned in the Job Description
2. **Mutually exclusive with improvements:** If a skill is flagged as an "improvement" (candidate has related skill), it should NOT appear in "gaps"
3. **Minimum 1 gap if score < 95:** If match_score is less than 95, at least one gap or improvement must be provided

### Improvement Suggestions Rules

1. **JD-aligned terminology:** Only suggest improvements when JD EXPLICITLY asks for a specific keyword
2. **Related concept exists:** Candidate must contain a related concept that can be rewritten
3. **No generic suggestions:** Do not suggest random or generic improvements

---

## Migration Instructions for Existing Deployments

### Database Migration

Run the migration script to add enhanced analysis columns to the `practice_sessions` table:

```bash
# Activate virtual environment
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

# Run migration
python scripts/migrate_enhanced_analysis.py
```

**Migration adds the following columns:**
- `enhanced_analysis` (JSONB) - Stores full enhanced analysis results
- `custom_additions` (TEXT) - Stores user-provided custom additions
- `improved_pdf_url` (VARCHAR(500)) - URL to generated improved PDF (optional)

### Backend Changes

1. **Enhanced Analyzer Service:** The `services/enhanced_analyzer.py` module is now integrated into the pipeline
2. **Orchestrator Updates:** `services/orchestrator.py` now calls enhanced analysis after basic parsing
3. **API Endpoints:** New endpoints `/refine` and `/pdf` are available in `api/routers/practice.py`

### Frontend Integration

1. **ResumeReport Component:** Display enhanced analysis on the assessment page
2. **CustomAdditionsForm Component:** Allow candidates to add custom information
3. **API Client Updates:** Add `refineCustomAdditions()` and `generatePDF()` functions

### Backward Compatibility

- Sessions without enhanced analysis will show `enhanced_analysis: null`
- Basic analysis results are preserved and still accessible
- PDF generation falls back gracefully if enhanced analysis is unavailable

### Testing the Migration

1. Create a new practice session and verify enhanced analysis runs automatically
2. Test the `/refine` endpoint with custom additions
3. Test the `/pdf` endpoint with different templates
4. Verify existing sessions still work without enhanced data

### Rollback Plan

If issues occur:
1. The migration is additive only - no data loss
2. Revert the code changes to the previous version
3. Existing sessions will continue to work with basic analysis

---

## Error Handling

### Common Errors

| Error Code | Description | Resolution |
|------------|-------------|------------|
| 404 | Session not found | Verify session_id and user ownership |
| 500 | PDF generation failed | Check reportlab installation: `pip install reportlab` |
| 500 | Failed to refine | Check LLM API key and quota |

### Logging

All errors are logged with session_id for debugging:
```
ERROR: Failed to generate PDF for session {session_id}: {error}
ERROR: Database error fetching session session_id={session_id}: {error}
```

---

## Rate Limiting

- PDF generation: 5 requests per session
- Refine endpoint: 10 requests per session

---

## Security Considerations

1. All endpoints require user authentication via `get_current_user_id()`
2. Users can only access their own sessions
3. Custom additions are sanitized before PDF generation
4. Template names are validated against allowed list
