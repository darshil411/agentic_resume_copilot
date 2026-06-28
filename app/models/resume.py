from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class Section(str, Enum):
    SUMMARY = "summary"
    SKILLS = "skills"
    PROJECTS = "projects"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    CERTIFICATIONS = "certifications"

class Project(BaseModel):
    title: str = Field(description="Title of the project")
    description: str = Field(description="A brief summary of what the project is")
    technologies: List[str] = Field(default_factory=list, description="Technologies and tools used in the project")
    impact: Optional[str] = Field(None, description="Quantifiable impact or outcome of the project, if any")

class Experience(BaseModel):
    company: str = Field(description="Name of the company or organization")
    role: str = Field(description="Job title or role")
    duration: str = Field(description="Duration of employment (e.g., 'Jan 2020 - Present')")
    bullets: List[str] = Field(default_factory=list, description="List of achievements and responsibilities")

class StructuredResume(BaseModel):
    """
    Strongly typed schema representing a parsed and structured resume.
    This serves as the canonical state for both the original and optimized resumes.
    """
    summary: str = Field(description="Professional summary or objective")
    skills: List[str] = Field(default_factory=list, description="List of technical and soft skills")
    projects: List[Project] = Field(default_factory=list, description="List of projects")
    experience: List[Experience] = Field(default_factory=list, description="List of work experiences")
    education: List[str] = Field(default_factory=list, description="List of educational qualifications")
    certifications: List[str] = Field(default_factory=list, description="List of certifications")
