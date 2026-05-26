# Requirements Document

## Introduction

Enhance the current resume analysis pipeline to provide candidates with a comprehensive ATS-friendly resume report that includes detailed scoring, gap identification, improvement suggestions, and the ability to generate an improved ATS-optimized PDF resume. This enhancement will be integrated into the practice session workflow, displayed on the assessment page before the interview begins.

## Glossary

- **ATS**: Applicant Tracking System - software used by employers to screen resumes
- **ATS Score**: A metric (0-100) indicating how well a resume is optimized for ATS parsing
- **Gap**: A missing skill, experience, or qualification explicitly mentioned in the Job Description but not present in the candidate's resume
- **Improvement**: A terminology suggestion to align resume phrasing with the Job Description's exact keywords
- **Custom Additions**: Additional information provided by the candidate to include in their improved resume (certifications, education, etc.)

## Requirements

### Requirement 1: Enhanced Resume Analysis

**User Story:** As a candidate, I want a detailed analysis of my resume against the job description so that I can understand exactly what needs improvement before my interview.

#### Acceptance Criteria

1. WHEN a practice session reaches the "ready_to_start" status, THE system SHALL run enhanced resume analysis that produces an ATS score, match score, identified gaps, and improvement suggestions.
2. WHILE the enhanced analysis is running, THE system SHALL maintain the session status as "ready_to_start" until completion.
3. IF enhanced analysis fails, THEN THE system SHALL log the error and allow the candidate to proceed with the interview using the basic analysis as fallback.

### Requirement 2: Gap and Improvement Display

**User Story:** As a candidate, I want to see my resume gaps and improvement suggestions so that I can understand what to address before the interview.

#### Acceptance Criteria

1. WHERE a practice session has completed enhanced analysis, THE system SHALL display the ATS score, match score, identified gaps, and improvement suggestions on the assessment page.
2. WHEN displaying gaps, THE system SHALL only show gaps for skills/requirements explicitly mentioned in the Job Description.
3. WHEN displaying improvements, THE system SHALL only suggest terminology changes when the Job Description explicitly asks for a specific keyword and the resume contains a related concept.

### Requirement 3: Custom Text Integration

**User Story:** As a candidate, I want to add custom information to my resume so that I can include additional certifications, education, or details that weren't in the original PDF.

#### Acceptance Criteria

1. WHERE the assessment page displays the resume report, THE system SHALL provide a text area for candidates to enter custom additions.
2. WHEN custom additions are submitted, THE system SHALL parse and categorize them (certificates, education, additional) and integrate them into the improved resume.
3. WHERE custom additions include prefixed sections (e.g., "certificate:", "education:"), THE system SHALL preserve those prefixes in the output.

### Requirement 4: Improved ATS-Optimized PDF Generation

**User Story:** As a candidate, I want to download an improved ATS-optimized version of my resume so that I can use it for future applications.

#### Acceptance Criteria

1. WHERE enhanced analysis is complete, THE system SHALL generate an ATS-optimized PDF resume that integrates gaps and improvements.
2. WHEN generating the PDF, THE system SHALL preserve all original content, only adding or improving where explicitly suggested.
3. IF a candidate provides custom additions with section prefixes, THE system SHALL create or update the appropriate section in the PDF.

### Requirement 5: Database Schema Update

**User Story:** As a developer, I want to store the enhanced analysis results so that they persist across sessions and can be retrieved for PDF generation.

#### Acceptance Criteria

1. WHEN enhanced analysis completes, THE system SHALL store the full analysis results including ATS score, gaps, improvements, and custom additions in the practice_sessions table.
2. WHERE the practice_sessions table lacks columns for enhanced data, THE system SHALL add them via a migration script.
3. THE system SHALL maintain backward compatibility with sessions that use only basic analysis.

### Requirement 6: API Endpoint for PDF Generation

**User Story:** As a candidate, I want to download my improved resume as a PDF so that I can save or share it.

#### Acceptance Criteria

1. WHEN a candidate requests PDF generation, THE system SHALL generate an ATS-optimized PDF using the enhanced analysis results and any custom additions.
2. WHERE template selection is provided, THE system SHALL support multiple resume templates (Classic ATS, Modern Accent, Two-Column Professional).
3. THE system SHALL return the PDF as a downloadable file with appropriate headers.

### Requirement 7: Frontend Assessment Page Update

**User Story:** As a candidate, I want to see my enhanced resume report on the assessment page so that I can review it before starting the interview.

#### Acceptance Criteria

1. WHEN the assessment page loads for a session with enhanced analysis, THE system SHALL display the ATS score, match score, gaps, and improvements.
2. WHERE custom additions are present, THE system SHALL show them and allow editing.
3. WHEN the candidate clicks "Download Improved Resume", THE system SHALL trigger PDF generation and download.

### Requirement 8: Migration from Basic to Enhanced Analysis

**User Story:** As a developer, I want to migrate existing sessions to use enhanced analysis so that all new sessions benefit from the improved scoring.

#### Acceptance Criteria

1. WHEN a new practice session is initialized, THE system SHALL use enhanced analysis by default.
2. WHERE a session exists with only basic analysis, THE system SHALL allow re-running enhanced analysis on demand.
3. THE system SHALL maintain both basic and enhanced analysis results for backward compatibility.
