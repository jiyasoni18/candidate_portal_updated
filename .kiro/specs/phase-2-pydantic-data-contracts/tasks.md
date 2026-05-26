# Implementation Plan

- [x] 1. Create the `schemas/` package and `__init__.py` with top-level exports





  - Create `schemas/` directory with an `__init__.py` that imports and re-exports `ResumeParsedData`, `ResumeReportData`, `QuestionArraySchema`, and `InterviewAssessmentSchema`
  - _Requirements: 1.1, 1.2_

- [x] 2. Implement `schemas/resume.py`





- [x] 2.1 Implement sub-models: `PersonalInfo`, `ExperienceItem`, `ProjectItem`, `EducationItem`


  - Write all four Pydantic v2 `BaseModel` classes with optional fields and `Field` descriptors as specified
  - _Requirements: 2.1, 2.2, 2.3, 2.4_


- [x] 2.2 Implement top-level models: `ResumeParsedData` and `ResumeReportData`




  - Compose sub-models into `ResumeParsedData`; add `score` constraint (ge=0, le=100) to `ResumeReportData`
  - Verify both models export valid JSON schema via `model_json_schema()` without errors
  - _Requirements: 2.5, 2.6, 2.7, 2.8, 5.1, 5.2_

- [x] 3. Implement `schemas/questions.py`






- [x] 3.1 Implement `GeneratedQuestionItem` and `QuestionArraySchema`

  - Write `GeneratedQuestionItem` with `Literal` category constraint and default `expected_duration_seconds`
  - Write `QuestionArraySchema` with `Field(min_length=8, max_length=8)` enforcing the exact 8-question contract
  - Verify `model_json_schema()` exports cleanly and that instantiation with wrong list length raises `ValidationError`
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 5.3_

- [x] 4. Implement `schemas/assessment.py`






- [x] 4.1 Implement `DimensionScoreCard` and `InterviewAssessmentSchema`

  - Write `DimensionScoreCard` with score bounds and `default_factory` list fields
  - Write `InterviewAssessmentSchema` with `Dict[str, DimensionScoreCard]`, `completion_ratio` (ge=0.0, le=1.0), and `overall_score` (ge=0, le=100) constraints
  - Verify `model_json_schema()` exports cleanly and that out-of-range values raise `ValidationError`
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 5.4_

- [x] 5. Write and run smoke-test validation script





- [x] 5.1 Create `schemas/smoke_test.py` with fixture-based instantiation checks


  - Instantiate each of the 4 top-level models with valid fixture data
  - Assert `model_dump()` returns a plain dict for each (JSONB compatibility check)
  - Run `python3 schemas/smoke_test.py` and confirm zero errors
  - _Requirements: 2.7, 2.8, 3.4, 4.3, 5.1, 5.2, 5.3, 5.4_
