from typing import List
from pydantic import BaseModel, Field

class ATSReport(BaseModel):
    """
    Hybrid ATS evaluation report combining deterministic and semantic analysis.
    """
    score: float = Field(description="Overall ATS match score (0.0 to 100.0)")
    matched_skills: List[str] = Field(default_factory=list, description="Skills present in both JD and resume")
    missing_skills: List[str] = Field(default_factory=list, description="Crucial JD skills missing from the resume")
    weak_sections: List[str] = Field(default_factory=list, description="Sections of the resume that need improvement (e.g., 'projects', 'experience')")
    improvement_suggestions: List[str] = Field(default_factory=list, description="Actionable suggestions to improve the ATS score")
