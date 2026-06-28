from pydantic import BaseModel # pyright: ignore[reportMissingImports]
from typing import List


class JDAnalysis(BaseModel):

    required_skills: List[str] = []

    responsibilities: List[str] = []

    tools_and_technologies: List[str] = []

    experience_requirements: List[str] = []

    keywords: List[str] = []

    role_summary: str