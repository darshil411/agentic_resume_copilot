from pydantic import BaseModel # pyright: ignore[reportMissingImports]
from typing import List, Optional


class Project(BaseModel):
    title: str
    description: str
    tech_stack: List[str] = []
    github_url: Optional[str] = None
    live_url: Optional[str] = None


class Experience(BaseModel):
    company: str
    role: str
    duration: Optional[str] = None
    bullets: List[str] = []


class Education(BaseModel):
    college: str
    degree: str
    year: Optional[str] = None
    cgpa: Optional[str] = None


class StructuredSkills(BaseModel):
    languages: List[str] = []
    frameworks: List[str] = []
    tools: List[str] = []
    databases: List[str] = []
    concepts: List[str] = []


class StructuredResume(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None

    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None

    summary: Optional[str] = None

    skills: StructuredSkills

    projects: List[Project] = []
    experience: List[Experience] = []
    education: List[Education] = []

    certifications: List[str] = []