from typing import List
from pydantic import BaseModel, Field

class JDAnalysis(BaseModel):
    """
    Structured analysis of a job description.
    """
    required_skills: List[str] = Field(default_factory=list, description="Explicitly required skills mentioned in the JD")
    responsibilities: List[str] = Field(default_factory=list, description="Key responsibilities expected in the role")
    keywords: List[str] = Field(default_factory=list, description="Important keywords or domain terms")
    tools: List[str] = Field(default_factory=list, description="Specific tools, software, or frameworks mentioned")
    experience_requirements: List[str] = Field(default_factory=list, description="Required years of experience or seniority level")
