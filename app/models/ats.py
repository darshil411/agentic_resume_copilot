from typing import List, Dict
from pydantic import BaseModel, Field

class ATSCategoryScores(BaseModel):
    keyword_match: float = Field(description="Out of 30")
    experience_alignment: float = Field(description="Out of 15")
    project_relevance: float = Field(description="Out of 15")
    quantifiable_impact: float = Field(description="Out of 10")
    resume_structure: float = Field(description="Out of 10")
    writing_quality: float = Field(description="Out of 10")
    penalties: float = Field(description="Negative points for keyword stuffing or repetition")

class ATSReport(BaseModel):
    score: float = Field(description="Final ATS Score (0-100)")
    category_scores: ATSCategoryScores
    matched_skills: List[str] = Field(default_factory=list, description="Skills present in both JD and resume")
    missing_skills: List[str] = Field(default_factory=list, description="Crucial JD skills missing from the resume")
    weak_sections: List[str] = Field(default_factory=list, description="Sections of the resume that need improvement (e.g., 'projects', 'experience')")
    improvement_priorities: List[str] = Field(default_factory=list, description="Ranked list of highest impact improvements")
    optimization_guidelines: Dict[str, List[str]] = Field(default_factory=dict, description="Guidelines for downstream AI agents per section")
    overall_feedback: List[str] = Field(default_factory=list, description="Max 5 concise feedback bullets")
