from pydantic import BaseModel
from typing import List

class ATSReport(BaseModel):
    # FIX: Use strings to allow outputs like "85" or "85%"
    ats_score: str 
    matched_skills: List[str] = []
    missing_skills: List[str] = []
    improvement_suggestions: List[str] = []
    keyword_match_percentage: str