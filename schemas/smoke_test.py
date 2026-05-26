"""
Smoke test: instantiate all 4 top-level schema models with valid fixture data
and assert model_dump() returns a plain dict (JSONB compatibility check).
"""

from schemas.resume import ResumeParsedData, ResumeReportData
from schemas.questions import QuestionArraySchema
from schemas.assessment import InterviewAssessmentSchema


# --- Fixtures ---

RESUME_PARSED_FIXTURE = {
    "personal_info": {
        "name": "Jane Doe",
        "email": "jane.doe@example.com",
        "phone": "+1-555-0100",
        "linkedin": "https://linkedin.com/in/janedoe",
        "github": "https://github.com/janedoe",
        "portfolio": "https://janedoe.dev",
    },
    "summary": "Experienced software engineer with 5 years in backend development.",
    "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
    "experience": [
        {
            "title": "Senior Backend Engineer",
            "company": "Acme Corp",
            "duration": "2021–2024",
            "description": "Led API development for a SaaS platform.",
        }
    ],
    "projects": [
        {
            "name": "OpenResume",
            "description": "Open-source resume parser.",
            "link": "https://github.com/janedoe/openresume",
        }
    ],
    "education": [
        {
            "degree": "B.Sc. Computer Science",
            "school": "State University",
            "year": "2019",
            "grade": "3.8 GPA",
        }
    ],
    "certifications": ["AWS Certified Developer"],
}

RESUME_REPORT_FIXTURE = {
    "score": 82,
    "reference_to_jd": "Candidate matches 82% of the job description requirements.",
    "strengths": ["Strong Python skills", "Relevant API experience"],
    "weaknesses": ["No Kubernetes experience", "Limited frontend exposure"],
}

QUESTIONS_FIXTURE = {
    "questions": [
        {"id": 1, "question": "Tell me about yourself.", "category": "opening"},
        {"id": 2, "question": "Describe your most recent role.", "category": "experience"},
        {"id": 3, "question": "Why are you interested in this position?", "category": "rolefit"},
        {"id": 4, "question": "Tell me about a time you handled conflict.", "category": "behavioral"},
        {"id": 5, "question": "How would you handle a production outage?", "category": "situational"},
        {"id": 6, "question": "What is your experience with microservices?", "category": "experience"},
        {"id": 7, "question": "How do you prioritize tasks under pressure?", "category": "behavioral"},
        {"id": 8, "question": "Do you have any questions for us?", "category": "closing"},
    ]
}

ASSESSMENT_FIXTURE = {
    "overall_score": 74,
    "practice_verdict": "Good",
    "summary": "Candidate demonstrated solid technical knowledge with room for improvement in communication.",
    "dimension_scores": {
        "Technical Familiarity": {
            "score": 80,
            "max_score": 100,
            "label": "Technical Familiarity",
            "verdict": "Strong",
            "evidence": "Correctly explained async patterns and database indexing.",
            "strengths": ["Clear explanations", "Accurate terminology"],
            "gaps": ["Did not mention caching strategies"],
        },
        "Communication": {
            "score": 68,
            "max_score": 100,
            "label": "Communication",
            "verdict": "Adequate",
            "evidence": "Answers were clear but occasionally verbose.",
            "strengths": ["Structured responses"],
            "gaps": ["Tendency to over-explain"],
        },
    },
    "overall_strengths": ["Technical depth", "Problem-solving approach"],
    "overall_gaps": ["Conciseness", "Caching knowledge"],
    "technical_round_probes": ["Ask about Redis usage", "Probe on system design experience"],
    "turns_analyzed": 8,
    "completion_ratio": 1.0,
}


# --- Smoke tests ---

def test_resume_parsed_data():
    model = ResumeParsedData.model_validate(RESUME_PARSED_FIXTURE)
    result = model.model_dump()
    assert isinstance(result, dict), "ResumeParsedData.model_dump() must return a dict"
    print("  ResumeParsedData OK")


def test_resume_report_data():
    model = ResumeReportData.model_validate(RESUME_REPORT_FIXTURE)
    result = model.model_dump()
    assert isinstance(result, dict), "ResumeReportData.model_dump() must return a dict"
    print("  ResumeReportData OK")


def test_question_array_schema():
    model = QuestionArraySchema.model_validate(QUESTIONS_FIXTURE)
    result = model.model_dump()
    assert isinstance(result, dict), "QuestionArraySchema.model_dump() must return a dict"
    assert len(result["questions"]) == 8, "QuestionArraySchema must contain exactly 8 questions"
    print("  QuestionArraySchema OK")


def test_interview_assessment_schema():
    model = InterviewAssessmentSchema.model_validate(ASSESSMENT_FIXTURE)
    result = model.model_dump()
    assert isinstance(result, dict), "InterviewAssessmentSchema.model_dump() must return a dict"
    print("  InterviewAssessmentSchema OK")


if __name__ == "__main__":
    print("Running schema smoke tests...")
    test_resume_parsed_data()
    test_resume_report_data()
    test_question_array_schema()
    test_interview_assessment_schema()
    print("All smoke tests passed.")
