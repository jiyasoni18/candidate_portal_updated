from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class DimensionScoreCard(BaseModel):
    score: int = Field(..., ge=0, le=100)
    max_score: int = 100
    label: str
    verdict: str
    evidence: str
    strengths: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)


class InterviewAssessmentSchema(BaseModel):
    overall_score: int = Field(..., ge=0, le=100)
    practice_verdict: str
    hire_recommendation: Optional[str] = None   # Strong Yes | Yes | Maybe | No | Strong No
    summary: str
    dimension_scores: Dict[str, DimensionScoreCard]
    overall_strengths: List[str]
    overall_gaps: List[str]
    red_flags: List[str] = Field(default_factory=list)
    technical_round_probes: List[str] = Field(default_factory=list)
    advance_to_technical: Optional[bool] = None
    advance_reasoning: Optional[str] = None
    candidate_level: Optional[str] = None       # fresher | junior | mid | senior
    interview_quality: Optional[str] = None     # complete | partial | incomplete
    turns_analyzed: int
    completion_ratio: float = Field(..., ge=0.0, le=1.0)
