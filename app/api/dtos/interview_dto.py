from pydantic import BaseModel # pyright: ignore[reportMissingImports]
from typing import List

class InterviewQuestionDTO(BaseModel):
    category: str
    question: str
    interviewer_intent: str
    project_to_highlight: str
    answer: str

class InterviewDeckDTO(BaseModel):
    thread_id: str
    status: str
    confidence_score: str
    source_basis: List[str] = []
    company_intel: List[str] = []
    experiences: List[str] = []
    company_questions: List[str] = []
    roadmap: List[str] = []
    questions: List[InterviewQuestionDTO] = []