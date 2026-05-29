from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class GeneratedQuestionItem(BaseModel):
    id: int
    question: str
    category: Optional[Literal["opening", "experience", "rolefit", "behavioral", "situational", "closing"]] = None
    expected_duration_seconds: int = 120


class QuestionArraySchema(BaseModel):
    questions: List[GeneratedQuestionItem] = Field(..., min_length=8, max_length=8)
