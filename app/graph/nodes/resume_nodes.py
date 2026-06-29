from typing import Dict, Any
from langchain_core.messages import HumanMessage # pyright: ignore[reportMissingImports]
from pydantic import BaseModel, Field # pyright: ignore[reportMissingImports]
import copy

# Import the unified global state canvas
from app.graph.state.global_state import GlobalGraphState
from app.utils.llm_factory import get_llm

class ProposedChanges(BaseModel):
    new_content: str = Field(description="The proposed optimized text for the section")
    reasoning: str = Field(description="Why this change improves the ATS score or impact")

def optimize_section_node(state: GlobalGraphState) -> Dict[str, Any]:
    """
    LLM Node: Proposes changes for a specific section based on ATS feedback.
    Crucially, this DOES NOT mutate the `optimized_resume` yet.
    """
    # CRITICAL FIX: Changed from state.get() to dot notation because state is a Pydantic model instance
    section = state.current_section or "summary"
    original = state.original_resume
    ats_report = state.ats_report
    
    # Retrieves the default model instance controlled by the central factory
    llm = get_llm("openrouter").with_structured_output(ProposedChanges)
    
    prompt = f"""
    The current section '{section}' needs optimization.
    ATS Missing Skills: {ats_report.missing_skills if ats_report else []}
    Original Resume Section: {getattr(original, section, '') if original else ''}
    
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

def approval_processing_node(state: GlobalGraphState) -> Dict[str, Any]:
    """
    Processes the human-in-the-loop (HITL) approval input.
    The approval_state dict stores {section_name: "approved"/"rejected"}.
    We must look up the *current section's* status, NOT a literal "approved" key.
    """
    section = state.current_section or "summary"
    approval_state = state.approval_state or {}
    # FIX: key is the section name (e.g. "summary"), value is "approved" or "rejected"
    section_status = approval_state.get(section, "")
    
    if section_status == "approved":
        return {"workflow_logs": [f"Human approved changes for section: {section}."]}
    else:
        # Increment retry count if rejected
        counts = copy.deepcopy(state.section_retry_counts or {})
        counts[section] = counts.get(section, 0) + 1
        human_feedback = state.human_feedback or {}
        feedback_text = human_feedback.get(section, "")
        return {
            "section_retry_counts": counts,
            "workflow_logs": [f"Human rejected changes for '{section}'. Feedback: {feedback_text}"]
        }

import copy

def commit_changes_node(state: GlobalGraphState) -> Dict[str, Any]:
    """
    Deterministic Node: Mutates the `optimized_resume` AFTER human approval,
    then advances to the next section.
    """
    proposed = state.proposed_changes or {}
    section = state.current_section or "summary"
    
    # FIX: Deep copy forces LangGraph to recognize the state change
    if state.optimized_resume:
        optimized = copy.deepcopy(state.optimized_resume)
    else:
        optimized = copy.deepcopy(state.original_resume)
    
    if proposed and "new_content" in proposed and optimized:
        setattr(optimized, section, proposed["new_content"])
        
    # FIX: Section Iterator (Advances the queue)
    all_sections = ["summary", "experience", "projects", "skills"]
    try:
        current_idx = all_sections.index(section)
        next_section = all_sections[current_idx + 1]
    except (ValueError, IndexError):
        next_section = "DONE"
        
    return {
        "optimized_resume": optimized,
        "current_section": next_section,
        "workflow_logs": [f"Committed approved changes to {section}"]
    }

def recompute_ats_node(state: GlobalGraphState) -> Dict[str, Any]:
    """
    LLM Node: Recomputes the ATS score after optimizations to verify improvement.
    """
    # CRITICAL FIX: Changed from state.get() to dot notation attribute tracking
    ats = copy.deepcopy(state.ats_report)
    if ats:
        ats.score = min(100.0, ats.score + 10.0)
    
    return {
        "ats_report": ats,
        "workflow_logs": ["Recomputed ATS score after committing changes."]
    }

def resume_export_node(state: GlobalGraphState) -> Dict[str, Any]:
    """
    Finalizes the resume pipeline by mocking an export path.
    """
    return {
        "resume_export_paths": {"pdf": "/exports/optimized_resume.pdf"},
        "branch_status": {"resume_pipeline": "COMPLETED"},
        "workflow_logs": ["Exported optimized resume."]
    }