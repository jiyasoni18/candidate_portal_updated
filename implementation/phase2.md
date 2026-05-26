# Phase 2: FastAPI Data Contracts & Pydantic Validation Models

## 1. Objective
Build the Pydantic v2 data models that will govern the request payloads, database JSONB storage validation, and API responses. This establishes an unshakeable type contract matching your original complex LLM data shapes.

## 2. Technical Contracts & Schemas

### 2.1. Resume Parsing Schema (`schemas/resume.py`)
This validates the JSON structure extracted from the candidate's PDF via the LLM parsing pipeline.

```python
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional

class PersonalInfo(BaseModel):
    name: Optional[str] = Field(None, description="Full name of the candidate")
    email: Optional[EmailStr] = Field(None, description="Contact email address")
    phone: Optional[str] = Field(None, description="Contact phone number")
    linkedin: Optional[str] = Field(None, description="LinkedIn profile URL")
    github: Optional[str] = Field(None, description="GitHub profile URL")
    portfolio: Optional[str] = Field(None, description="Personal portfolio or website URL")

class ExperienceItem(BaseModel):
    title: Optional[str] = Field(None, description="Job title held")
    company: Optional[str] = Field(None, description="Name of the employer")
    duration: Optional[str] = Field(None, description="Timeframe or dates of employment")
    description: Optional[str] = Field(None, description="Key duties and achievements")

class ProjectItem(BaseModel):
    name: Optional[str] = Field(None, description="Project title")
    description: Optional[str] = Field(None, description="Summary of tech stack and project purpose")
    link: Optional[str] = Field(None, description="Repository or live deployment link")

class EducationItem(BaseModel):
    degree: Optional[str] = Field(None, description="Degree or certification earned")
    school: Optional[str] = Field(None, description="Institution name")
    year: Optional[str] = Field(None, description="Graduation year")
    grade: Optional[str] = Field(None, description="GPA, percentage, or class honors")

class ResumeParsedData(BaseModel):
    personal_info: PersonalInfo
    summary: Optional[str] = Field(None, description="Professional summary snippet")
    skills: List[str] = Field(default_factory=list, description="Extracted tech stack and hard/soft skills")
    experience: List[ExperienceItem] = Field(default_factory=list)
    projects: List[ProjectItem] = Field(default_factory=list)
    education: List[EducationItem] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)

class ResumeReportData(BaseModel):
    score: int = Field(..., ge=0, le=100, description="Resume alignment score out of 100 against target JD")
    reference_to_jd: str = Field(..., description="High-level narrative explaining the alignment details")
    strengths: List[str] = Field(..., description="Key professional or technical advantages identified")
    weaknesses: List[str] = Field(..., description="Gaps, missing skills, or areas for improvement against the JD")

2.2. Custom Question Generation Schema (schemas/questions.py)
Validates the enriched, non-theoretical narrative list consisting of exactly 8 customized questions passed down to the LiveKit agent.

from pydantic import BaseModel, Field
from typing import List, Literal

class GeneratedQuestionItem(BaseModel):
    id: int = Field(..., description="Sequential question number from 1 to 8")
    question: str = Field(..., description="The conversational, non-robotic interview question string")
    category: Literal['opening', 'experience', 'rolefit', 'behavioral', 'situational', 'closing']
    expected_duration_seconds: int = Field(default=120, description="Recommended answer timer for the UI")

class QuestionArraySchema(BaseModel):
    questions: List[GeneratedQuestionItem] = Field(..., max_items=8, min_items=8)


2.3. Post-Interview Performance Grading Schema (schemas/assessment.py)
Governs the multi-dimensional, completion-weighted evaluation output computed over the live voice session transcript.

from pydantic import BaseModel, Field
from typing import List, Dict

class DimensionScoreCard(BaseModel):
    score: int = Field(..., ge=0, le=100)
    max_score: int = Field(default=100)
    label: str = Field(..., description="Dimension title (e.g., Technical Familiarity, Communication)")
    verdict: str = Field(..., description="Qualitative grade (e.g., Strong, Good, Needs Improvement)")
    evidence: str = Field(..., description="Direct quotes or explicit behaviors seen in transcript")
    strengths: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)

class InterviewAssessmentSchema(BaseModel):
    overall_score: int = Field(..., ge=0, le=100, description="Completion-weighted final grade")
    practice_verdict: str = Field(..., description="Summary operational evaluation (e.g., High Alignment, Mid Alignment)")
    summary: str = Field(..., description="Comprehensive feedback breakdown for the candidate's review")
    dimension_scores: Dict[str, DimensionScoreCard]
    overall_strengths: List[str]
    overall_gaps: List[str]
    technical_round_probes: List[str] = Field(default_factory=list, description="Deep-dive topics for real technical rounds")
    turns_analyzed: int
    completion_ratio: float = Field(..., ge=0.0, le=1.0)


3. Verification Check Constraints
The Kiro agent must verify successful completion by running a Python compile validation test on these schema definitions using standard Pydantic schema exports:

python3 -c "from schemas.resume import ResumeParsedData; print(ResumeParsedData.model_json_schema())"

Ensure no validation or dependency structural errors throw.
