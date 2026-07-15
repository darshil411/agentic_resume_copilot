from typing import List, Optional
from pydantic import BaseModel, Field

class JDAnalysis(BaseModel):
    company_name: Optional[str] = Field(default="Generic Company", description="The name of the company offering the job, extracted from the text")
    industry: Optional[str] = Field(default="Technology", description="The industry domain, e.g., AI, FinTech, E-commerce")
    role_summary: str = Field(description="High-level summary of the role")
    required_skills: List[str] = Field(description="List of core required skills and technologies")
    responsibilities: List[str] = Field(description="Key responsibilities and duties")
    keywords: List[str] = Field(description="ATS keywords extracted from the JD")
    tools: List[str] = Field(description="Specific tools, software, or platforms mentioned")
    experience_requirements: str = Field(description="Years or depth of experience required")
