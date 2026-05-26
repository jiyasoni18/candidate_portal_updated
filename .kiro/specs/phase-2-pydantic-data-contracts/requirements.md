# Requirements Document

## Introduction

Phase 2 establishes the Pydantic v2 data contract layer for the Candidate Interview Practice Portal. This phase defines all typed schema models that govern request payloads, JSONB column validation, and API response serialization across the three core LLM pipeline outputs: resume parsing, interview question generation, and post-interview performance assessment. These schemas form the unshakeable type contract that all subsequent FastAPI route handlers, background task pipelines, and the LiveKit voice agent will depend on. No HTTP endpoints are implemented in this phase — only the schema definitions and their structural validation.

## Glossary

- **Pydantic v2**: The Python data validation library used to define typed, validated data models via `BaseModel`. All models in this phase use the v2 API (`model_json_schema()`, `model_validate()`, etc.).
- **Schema Module**: A Python file under the `schemas/` package directory containing one or more Pydantic `BaseModel` class definitions.
- **ResumeParsedData**: The top-level Pydantic model representing the structured JSON output of the LLM resume extraction pipeline, stored in the `resume_parsed` JSONB column.
- **ResumeReportData**: The Pydantic model representing the alignment scoring report output, stored in the `resume_report` JSONB column.
- **GeneratedQuestionItem**: A Pydantic model representing a single AI-generated interview question with metadata, stored as an element within the `generated_questions` JSONB array.
- **QuestionArraySchema**: The top-level Pydantic model wrapping exactly 8 `GeneratedQuestionItem` entries passed to the LiveKit voice agent via Room Metadata.
- **DimensionScoreCard**: A Pydantic model representing a single evaluated performance dimension from the post-interview transcript analysis.
- **InterviewAssessmentSchema**: The top-level Pydantic model representing the full completion-weighted post-interview performance report, stored in the `interview_assessment` JSONB column.
- **JSONB Column**: A PostgreSQL binary JSON column type defined in Phase 1's `init.sql` schema. The Pydantic models in this phase must be structurally compatible with the data stored in these columns.
- **Question Category**: A constrained string literal type for `GeneratedQuestionItem.category`, limited to: `opening`, `experience`, `rolefit`, `behavioral`, `situational`, `closing`.
- **Completion Ratio**: A float between 0.0 and 1.0 representing the fraction of the 8 interview questions that were answered before the session ended, used as a weighting factor in the overall score.
- **`schemas/` Package**: The top-level Python package directory (`schemas/__init__.py`) that groups all schema modules for clean import resolution.

---

## Requirements

### Requirement 1

**User Story:** As a backend developer, I want a `schemas/` Python package initialized with an `__init__.py`, so that all schema modules are importable from a single, consistent namespace.

#### Acceptance Criteria

1. THE Schema Module SHALL exist as a directory named `schemas/` at the project root containing an `__init__.py` file.
2. THE `schemas/__init__.py` file SHALL export `ResumeParsedData`, `ResumeReportData`, `QuestionArraySchema`, and `InterviewAssessmentSchema` so they are importable directly from the `schemas` namespace.

---

### Requirement 2

**User Story:** As a backend developer, I want a `schemas/resume.py` module defining the resume parsing and scoring data contracts, so that LLM-extracted resume JSON and alignment report JSON can be validated before being written to the `resume_parsed` and `resume_report` JSONB columns.

#### Acceptance Criteria

1. THE `schemas/resume.py` module SHALL define a `PersonalInfo` model with optional fields: `name` (str), `email` (EmailStr), `phone` (str), `linkedin` (str), `github` (str), and `portfolio` (str).
2. THE `schemas/resume.py` module SHALL define an `ExperienceItem` model with optional fields: `title` (str), `company` (str), `duration` (str), and `description` (str).
3. THE `schemas/resume.py` module SHALL define a `ProjectItem` model with optional fields: `name` (str), `description` (str), and `link` (str).
4. THE `schemas/resume.py` module SHALL define an `EducationItem` model with optional fields: `degree` (str), `school` (str), `year` (str), and `grade` (str).
5. THE `schemas/resume.py` module SHALL define a `ResumeParsedData` model that composes `PersonalInfo`, `List[ExperienceItem]`, `List[ProjectItem]`, `List[EducationItem]`, and list fields for `skills` (List[str]) and `certifications` (List[str]), with an optional `summary` (str) field.
6. THE `schemas/resume.py` module SHALL define a `ResumeReportData` model with required fields: `score` (int, constrained 0–100), `reference_to_jd` (str), `strengths` (List[str]), and `weaknesses` (List[str]).
7. WHEN `ResumeParsedData.model_json_schema()` is called, THE Pydantic v2 runtime SHALL return a valid JSON schema dict without raising a `ValidationError` or `PydanticUserError`.
8. WHEN `ResumeReportData.model_json_schema()` is called, THE Pydantic v2 runtime SHALL return a valid JSON schema dict without raising a `ValidationError` or `PydanticUserError`.

---

### Requirement 3

**User Story:** As a backend developer, I want a `schemas/questions.py` module defining the interview question generation contract, so that the LLM output can be validated to contain exactly 8 structured questions before being stored in the `generated_questions` JSONB column and injected into LiveKit Room Metadata.

#### Acceptance Criteria

1. THE `schemas/questions.py` module SHALL define a `GeneratedQuestionItem` model with required fields: `id` (int), `question` (str), and `category` (Literal constrained to `opening`, `experience`, `rolefit`, `behavioral`, `situational`, `closing`), and an optional `expected_duration_seconds` (int, default 120).
2. THE `schemas/questions.py` module SHALL define a `QuestionArraySchema` model with a `questions` field typed as `List[GeneratedQuestionItem]` constrained to a minimum of 8 and a maximum of 8 items.
3. WHEN a `QuestionArraySchema` is instantiated with fewer than 8 or more than 8 items in the `questions` list, THE Pydantic v2 runtime SHALL raise a `ValidationError`.
4. WHEN `QuestionArraySchema.model_json_schema()` is called, THE Pydantic v2 runtime SHALL return a valid JSON schema dict without raising a `ValidationError` or `PydanticUserError`.

---

### Requirement 4

**User Story:** As a backend developer, I want a `schemas/assessment.py` module defining the post-interview performance grading contract, so that the transcript analysis pipeline output can be validated before being written to the `interview_assessment` JSONB column.

#### Acceptance Criteria

1. THE `schemas/assessment.py` module SHALL define a `DimensionScoreCard` model with required fields: `score` (int, constrained 0–100), `max_score` (int, default 100), `label` (str), `verdict` (str), and `evidence` (str), and optional list fields `strengths` (List[str]) and `gaps` (List[str]).
2. THE `schemas/assessment.py` module SHALL define an `InterviewAssessmentSchema` model with required fields: `overall_score` (int, constrained 0–100), `practice_verdict` (str), `summary` (str), `dimension_scores` (Dict[str, DimensionScoreCard]), `overall_strengths` (List[str]), `overall_gaps` (List[str]), `turns_analyzed` (int), and `completion_ratio` (float, constrained 0.0–1.0), and an optional `technical_round_probes` (List[str], default empty list).
3. WHEN `InterviewAssessmentSchema.model_json_schema()` is called, THE Pydantic v2 runtime SHALL return a valid JSON schema dict without raising a `ValidationError` or `PydanticUserError`.
4. WHEN an `InterviewAssessmentSchema` is instantiated with a `completion_ratio` value outside the range 0.0 to 1.0, THE Pydantic v2 runtime SHALL raise a `ValidationError`.
5. WHEN an `InterviewAssessmentSchema` is instantiated with an `overall_score` value outside the range 0 to 100, THE Pydantic v2 runtime SHALL raise a `ValidationError`.

---

### Requirement 5

**User Story:** As a backend developer, I want all schema modules to be structurally compatible with the Phase 1 JSONB columns, so that validated Pydantic model instances can be serialized directly into the `resume_parsed`, `resume_report`, `generated_questions`, and `interview_assessment` columns without transformation.

#### Acceptance Criteria

1. THE `ResumeParsedData` model SHALL be serializable to a JSON-compatible dict via `model.model_dump()` that matches the structure expected by the `resume_parsed` JSONB column defined in Phase 1.
2. THE `ResumeReportData` model SHALL be serializable to a JSON-compatible dict via `model.model_dump()` that matches the structure expected by the `resume_report` JSONB column defined in Phase 1.
3. THE `QuestionArraySchema` model SHALL be serializable to a JSON-compatible dict via `model.model_dump()` that matches the structure expected by the `generated_questions` JSONB column defined in Phase 1.
4. THE `InterviewAssessmentSchema` model SHALL be serializable to a JSON-compatible dict via `model.model_dump()` that matches the structure expected by the `interview_assessment` JSONB column defined in Phase 1.
