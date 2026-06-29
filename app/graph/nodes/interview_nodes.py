from typing import Dict, Any, List
from langchain_core.messages import HumanMessage # pyright: ignore[reportMissingImports]
from pydantic import BaseModel, Field # pyright: ignore[reportMissingImports]

# Imported GlobalGraphState to ensure strict type synchronization across subgraphs
from app.graph.state.global_state import GlobalGraphState
from app.utils.llm_factory import get_llm

class InterviewPrepOutput(BaseModel):
    questions: List[str] = Field(description="List of technical and behavioral interview questions")
    experiences: List[str] = Field(description="Summary of likely interview experiences or round structure")
    roadmap: List[str] = Field(description="Step-by-step preparation roadmap")

def generate_interview_prep_node(state: GlobalGraphState) -> Dict[str, Any]:
    """
    LLM Node: Generates interview questions and prep material.
    Crucially, it uses `original_resume` to remain strictly independent of the resume optimization pipeline.
    """
    # FIX: Switched from state.get() to standard Pydantic dot-notation to avoid AttributeError crashes
    resume = state.original_resume
    jd_analysis = state.jd_analysis
    
    if not resume or not jd_analysis:
        return {"errors": ["Missing original_resume or jd_analysis for interview prep."]}
        
    # Uses centralized factory default for Gemini ("gemini-3.5-flash" or equivalent modern 2026 model)
    llm = get_llm("gemini").with_structured_output(InterviewPrepOutput)
    
    prompt = f"""
    Based on the original resume and the job description analysis, generate an interview preparation guide.
    Do not assume any optimizations have been made to the resume.
    
    Original Resume Skills: {resume.skills}
    JD Required Skills: {jd_analysis.required_skills}
    """
    
    try:
        output = llm.invoke([HumanMessage(content=prompt)])
        return {
            "interview_questions": output.questions,
            "interview_experiences": output.experiences,
            "prep_roadmap": output.roadmap,
            "branch_status": {"interview_pipeline": "COMPLETED"},
            "workflow_logs": ["Generated interview preparation materials."]
        }
    except Exception as e:
        return {"errors": [f"generate_interview_prep_node failed: {str(e)}"]}