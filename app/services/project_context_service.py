import logging
from typing import List
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from app.utils.llm_factory import get_llm

logger = logging.getLogger(__name__)
MAX_SELECTION_CHARS = 2000

class ProjectSelection(BaseModel):
    selected_indices: List[int] = Field(description="List of indices (0-indexed) of the most relevant project documents.")

def select_relevant_projects(jd_text: str, project_texts: List[str]) -> List[str]:
    """
    Evaluates project texts and selects the top 2-3 most relevant ones based on the JD.
    """
    if not project_texts:
        return []
        
    if len(project_texts) <= 3:
        return project_texts
        
    try:
        llm = get_llm("openrouter").with_structured_output(ProjectSelection)
        
        projects_formatted = ""
        for i, pt in enumerate(project_texts):
            # Limit the text passed to avoid context overflow during selection
            snippet = pt[:MAX_SELECTION_CHARS]
            projects_formatted += f"--- Project {i} ---\n{snippet}\n\n"

        #PLANER LOGIC PROMPT TO DECIDE WHICH PROJECTS TO SELECT TO MAXIMIZE ATS SCORE 

        prompt = f"""
        You are a Senior Technical Recruiter and Resume Strategy Planner.

        Your task is to identify which uploaded project documents provide the strongest supporting evidence for tailoring a resume to the given Job Description.

        You are NOT summarizing projects.

        You are deciding which projects should influence resume optimization.

        =========================
        JOB DESCRIPTION
        =========================

        {jd_text}

        =========================
        UPLOADED PROJECT DOCUMENTS
        =========================

        {projects_formatted}

        Evaluate every project using the following priorities:

        1. Technology stack overlap
        2. Required frameworks
        3. Backend / Frontend / AI / Cloud domain similarity
        4. Responsibilities matching the JD
        5. System architecture relevance
        6. Production engineering practices
        7. APIs, databases and infrastructure
        8. Scalability and performance work
        9. Quantifiable achievements
        10. Overall technical depth

        Ignore completely:
        - Installation instructions
        - Setup steps
        - Folder structures
        - Screenshots
        - Badges
        - Changelogs
        - Roadmaps
        - Contribution guides
        - Licenses
        - Markdown formatting

        Return ONLY the indices of the best 2–3 projects.

        Do not explain your reasoning.
        Do not output anything except the indices.
        """
        
        result = llm.invoke([HumanMessage(content=prompt)])
        selected = []
        for idx in result.selected_indices:
            if 0 <= idx < len(project_texts):
                selected.append(project_texts[idx])
                
        # Fallback if LLM returns empty list
        if not selected:
            return project_texts[:3]
            
        return selected
    except Exception as e:
        logger.error(f"Failed to select relevant projects: {e}")
        # Fallback to just taking the first 3
        return project_texts[:3]

class ContextCompression(BaseModel):
    context: str = Field(description="The compressed ATS-focused project context.")

def build_project_context(selected_project_texts: List[str]) -> str:
    """
    Compresses the selected projects into an ATS-focused context string.
    """
    if not selected_project_texts:
        return ""
        
    try:
        llm = get_llm("gemini").with_structured_output(ContextCompression)
        
        projects_formatted = "\n\n=== NEXT PROJECT ===\n\n".join(selected_project_texts)
        
        prompt = f"""
        You are a Staff Software Engineer and Technical Resume Reviewer.

        You are building an INTERNAL PROJECT KNOWLEDGE BASE that will later be consumed by another LLM responsible for optimizing a resume.

        Your objective is NOT to write resume bullets.

        Your objective is to preserve the maximum amount of useful engineering information while removing everything irrelevant.

        ====================================================
        PROJECT DOCUMENTS
        ====================================================

        {projects_formatted}

        ====================================================
        FOR EACH PROJECT RETURN THE FOLLOWING FORMAT
        ====================================================

        PROJECT

        Name:
        (If identifiable, otherwise infer a short descriptive name.)

        Business Problem:
        What real problem does this project solve?

        Project Summary:
        2-4 concise sentences describing the system.

        Tech Stack:
        Languages
        Frameworks
        Libraries
        Databases
        Cloud
        APIs
        AI Models
        Vector Databases
        DevOps
        Other Tools

        Architecture:
        Explain the important architecture decisions.

        Engineering Highlights:
        Backend systems
        Scalability
        Concurrency
        Caching
        RAG
        Agentic workflows
        Authentication
        Streaming
        Pipelines
        Optimization
        Performance
        Security
        Database design

        Responsibilities:
        What did the developer actually build?

        Measurable Impact:
        Only include verified metrics.

        ATS Keywords:
        Return every important technical keyword found.

        ====================================================
        REMOVE
        ====================================================

        Remove

        Installation

        Setup

        Folder Structure

        Screenshots

        Future Work

        License

        Contributors

        Deployment Instructions

        Formatting

        Code snippets

        ====================================================
        RULES
        ====================================================

        Preserve project boundaries.

        Never merge two projects.

        Never invent information.

        Never remove important technologies.

        Never remove architecture decisions.

        Never remove engineering achievements.

        Keep every project independent.

        The next LLM will compare these projects against resume projects.

        Therefore preserving project identity is more important than making the output shorter.

        Output ONLY the structured project knowledge base.
        """
        
        result = llm.invoke([HumanMessage(content=prompt)])
        return result.context
    except Exception as e:
        logger.error(f"Failed to build project context: {e}")
        return ""
