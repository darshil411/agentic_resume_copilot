from typing import Dict, Any, List
from langchain_core.messages import HumanMessage  # pyright: ignore[reportMissingImports]
from pydantic import BaseModel, Field  # pyright: ignore[reportMissingImports]

from app.graph.state.global_state import GlobalGraphState
from app.utils.llm_factory import get_llm


class InterviewPrepOutput(BaseModel):
    questions: List[str] = Field(description="List of technical and behavioral interview questions")
    experiences: List[str] = Field(description="Summary of likely interview experiences or round structure")
    roadmap: List[str] = Field(description="Step-by-step preparation roadmap")


_FALLBACK_QUESTIONS = [
    "Tell me about yourself and your engineering background.",
    "Walk me through your most impactful project end-to-end.",
    "How do you approach debugging a production issue under pressure?",
    "Describe a time you had to learn a new technology quickly.",
    "How do you ensure code quality in a fast-moving team?",
]
_FALLBACK_EXPERIENCES = ["Technical phone screen", "System design round", "Coding challenge", "Behavioral/HR round"]
_FALLBACK_ROADMAP = [
    "Review core CS fundamentals (data structures, algorithms)",
    "Prepare 3-5 STAR-format project stories",
    "Practice system design for distributed services",
    "Research the company's engineering blog and tech stack",
]


def generate_interview_prep_node(state: GlobalGraphState) -> Dict[str, Any]:
    """
    LLM Node: Generates interview questions and prep material.
    Primary: Groq (llama-3.1-8b-instant)  |  Fallback: Gemini (with key rotation)
    Uses original_resume to stay independent of the resume optimization pipeline.
    """
    resume = state.original_resume
    jd_analysis = state.jd_analysis

    if not resume or not jd_analysis:
        return {"errors": ["Missing original_resume or jd_analysis for interview prep."]}

    prompt = f"""
    Based on the candidate's original resume and the job description analysis,
    generate a practical interview preparation guide.
    Do NOT assume the resume has been optimized.

    Original Resume Skills: {resume.skills}
    JD Required Skills: {jd_analysis.required_skills}
    JD Responsibilities: {jd_analysis.responsibilities}
    """

    # Primary: Groq llama-3.1-8b-instant
    try:
        llm = get_llm("groq").with_structured_output(InterviewPrepOutput)
        output = llm.invoke([HumanMessage(content=prompt)])
        return {
            "interview_questions": output.questions,
            "interview_experiences": output.experiences,
            "prep_roadmap": output.roadmap,
            "branch_status": {"interview_pipeline": "COMPLETED"},
            "workflow_logs": ["[Groq/llama-3.1-8b] Generated interview preparation materials."]
        }
    except Exception:
        pass  # fall through to Gemini

    # Fallback: Gemini with key rotation
    try:
        llm = get_llm("gemini").with_structured_output(InterviewPrepOutput)
        output = llm.invoke([HumanMessage(content=prompt)])
        return {
            "interview_questions": output.questions,
            "interview_experiences": output.experiences,
            "prep_roadmap": output.roadmap,
            "branch_status": {"interview_pipeline": "COMPLETED"},
            "workflow_logs": ["[Gemini fallback] Generated interview preparation materials."]
        }
    except Exception as e:
        # Hard fallback: generic questions so the branch doesn't kill the graph
        return {
            "interview_questions": _FALLBACK_QUESTIONS,
            "interview_experiences": _FALLBACK_EXPERIENCES,
            "prep_roadmap": _FALLBACK_ROADMAP,
            "branch_status": {"interview_pipeline": "COMPLETED"},
            "workflow_logs": [f"[Hard fallback] Used generic interview prep. Both providers failed: {e}"],
            "errors": [f"generate_interview_prep_node: all providers failed: {str(e)}"]
        }