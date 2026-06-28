from pydantic import BaseModel # pyright: ignore[reportMissingImports]
from typing import List
from ..state import GraphState
from ...schemas.resume import Project
from ...services.llm_service import get_llm
from ...prompts.optimization_prompts import PROJECT_OPTIMIZATION_PROMPT
import time

# FIX: Create a wrapper model to ensure the LLM returns a list of projects
class ProjectList(BaseModel):
    projects: List[Project]

def optimize_projects_node(state: GraphState):
    llm = get_llm()
    
    # FIX: Force the LLM to output the structured List[Project] format
    structured_llm = llm.with_structured_output(ProjectList)

    # Fallback to an empty list if original_resume isn't populated for some reason
    current_projects = state.original_resume.projects if state.original_resume else []
    feedback = state.human_feedback.get("projects", "")
    
    time.sleep(5)
    response = structured_llm.invoke(
        f"""
        {PROJECT_OPTIMIZATION_PROMPT}

        Human Feedback:
        {feedback}

        Current Projects:
        {current_projects}

        ATS Report:
        {state.ats_report}
        """
    )

    return {
        "current_section": "projects",
        "proposed_changes": {
            "projects": response.projects  # Now safely passes a List[Project]
        }
    }