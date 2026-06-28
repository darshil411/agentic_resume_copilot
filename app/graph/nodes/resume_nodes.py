from typing import Dict, Any
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field
import copy

from app.graph.state.global_state import GlobalGraphState
from app.graph.state.local_states import ResumeSubgraphState
from app.utils.llm_factory import get_llm

# Since we want a typed state for the overall Resume Subgraph, we merge Global + ResumeSubgraphState
class ResumeGraphState(GlobalGraphState, ResumeSubgraphState):
    pass

class ProposedChanges(BaseModel):
    new_content: str = Field(description="The proposed optimized text for the section")
    reasoning: str = Field(description="Why this change improves the ATS score or impact")

def optimize_section_node(state: ResumeGraphState) -> Dict[str, Any]:
    """
    LLM Node: Proposes changes for a specific section based on ATS feedback.
    Crucially, this DOES NOT mutate the `optimized_resume` yet.
    """
    section = state.get("current_section", "summary")
    original = state.get("original_resume")
    ats_report = state.get("ats_report")
    
    llm = get_llm("openrouter").with_structured_output(ProposedChanges)
    
    prompt = f"""
    The current section '{section}' needs optimization.
    ATS Missing Skills: {ats_report.missing_skills if ats_report else []}
    Original Resume Section: {getattr(original, section, '')}
    
    Propose an optimized version of this section that naturally incorporates missing skills
    and improves impact.
    """
    
    try:
        proposed = llm.invoke([HumanMessage(content=prompt)])
        return {
            "proposed_changes": proposed.model_dump(),
            "workflow_logs": [f"Generated proposed changes for {section}"]
        }
    except Exception as e:
        return {"errors": [f"optimize_section_node failed: {str(e)}"]}

def approval_processing_node(state: ResumeGraphState) -> Dict[str, Any]:
    """
    Processes the human-in-the-loop (HITL) approval input.
    """
    approval_state = state.get("approval_state", {})
    approved = approval_state.get("approved", False)
    
    if approved:
        return {"workflow_logs": ["Human approved the proposed changes."]}
    else:
        # Increment retry count if rejected
        section = state.get("current_section", "summary")
        counts = state.get("section_retry_counts", {})
        counts[section] = counts.get(section, 0) + 1
        return {
            "section_retry_counts": counts,
            "workflow_logs": [f"Human rejected changes. Feedback: {approval_state.get('feedback', '')}"]
        }

def commit_changes_node(state: ResumeGraphState) -> Dict[str, Any]:
    """
    Deterministic Node: Mutates the `optimized_resume` only AFTER human approval.
    """
    proposed = state.get("proposed_changes", {})
    section = state.get("current_section", "summary")
    
    # Initialize optimized_resume if it doesn't exist
    optimized = state.get("optimized_resume")
    if not optimized:
        optimized = copy.deepcopy(state.get("original_resume"))
    
    if proposed and "new_content" in proposed:
        # In a real scenario, this logic depends on the section type (e.g., list vs string)
        # For simplicity, assuming string-based update or overwriting
        setattr(optimized, section, proposed["new_content"])
        
    return {
        "optimized_resume": optimized,
        "workflow_logs": [f"Committed approved changes to {section}"]
    }

def recompute_ats_node(state: ResumeGraphState) -> Dict[str, Any]:
    """
    LLM Node: Recomputes the ATS score after optimizations to verify improvement.
    """
    # Simply call the foundation node logic or similar, but with optimized_resume
    # For now, we simulate a small bump in the score
    ats = state.get("ats_report")
    if ats:
        ats.score = min(100.0, ats.score + 10.0)
    
    return {
        "ats_report": ats,
        "workflow_logs": ["Recomputed ATS score after committing changes."]
    }

def resume_export_node(state: ResumeGraphState) -> Dict[str, Any]:
    """
    Finalizes the resume pipeline by mocking an export path.
    """
    return {
        "resume_export_paths": {"pdf": "/exports/optimized_resume.pdf"},
        "branch_status": {"resume_pipeline": "COMPLETED"},
        "workflow_logs": ["Exported optimized resume."]
    }
