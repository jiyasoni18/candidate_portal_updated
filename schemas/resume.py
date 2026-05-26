from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


class PersonalInfo(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None


class ExperienceItem(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    duration: Optional[str] = None
    description: Optional[str] = None


class ProjectItem(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    link: Optional[str] = None


class EducationItem(BaseModel):
    degree: Optional[str] = None
    school: Optional[str] = None
    year: Optional[str] = None
    grade: Optional[str] = None


class ResumeParsedData(BaseModel):
    personal_info: PersonalInfo
    summary: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    experience: List[ExperienceItem] = Field(default_factory=list)
    projects: List[ProjectItem] = Field(default_factory=list)
    education: List[EducationItem] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)


class ResumeReportData(BaseModel):
    score: int = Field(..., ge=0, le=100)
    reference_to_jd: str
    strengths: List[str]
    weaknesses: List[str]


class EnhancedAnalysisSchema(BaseModel):
    match_score: int = Field(..., ge=0, le=100)
    ats_score: int = Field(..., ge=0, le=100)
    ats_explanation: str
    gaps: List[str]
    improvements: List[str]
    core_strengths: List[str]
    summary: str
    explanation: str
