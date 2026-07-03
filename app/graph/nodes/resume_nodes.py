from typing import Dict, Any
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field
import copy
from langgraph.types import interrupt
from app.graph.state.global_state import GlobalGraphState
from app.utils.llm_factory import get_llm

class ProposedChanges(BaseModel):
    new_content: str = Field(description="The proposed optimized text for the section")
    reasoning: str = Field(description="Why this change improves the ATS score or impact")

def _is_section_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, list):
        return len(value) == 0
    text = str(value).strip()
    return text == "" or text.lower() in ("none", "null")

def optimize_section_node(state: GlobalGraphState) -> Dict[str, Any]:
    section = state.current_section or "summary"
    original = state.original_resume
    ats_report = state.ats_report
    
    # Safely extract feedback
    feedback_dict = state.human_feedback or {}
    feedback_text = feedback_dict.get(section, "")

    raw_section = getattr(original, section, '') if original else ''

    # Auto-skip empty sections deterministically
    if _is_section_empty(raw_section):
        return {
            "workflow_logs": [f"Skipped optimization for missing section: {section}"],
            "approval_state": {section: "skipped"}
        }

    current_text = "\n".join([str(x) for x in raw_section]) if isinstance(raw_section, list) else str(raw_section).strip()

    feedback_block = (
        f"\n\nIMPORTANT: The human reviewer rejected the previous draft with this feedback:\n"
        f"\"{feedback_text}\"\n"
        f"You MUST incorporate this feedback directly in the new version."
        if feedback_text else ""
    )

    prompt = f"""
    The current resume section '{section}' needs optimization for the target job.
    ATS Missing Skills: {ats_report.missing_skills if ats_report else []}
    Original Resume Section Data: {current_text}
    {feedback_block}

    Propose an optimized version of this section that naturally incorporates missing skills
    and improves impact. Format the output as clean, professional plain text or markdown.
    """

    try:
        llm = get_llm("cerebras").with_structured_output(ProposedChanges)
        proposed = llm.invoke([HumanMessage(content=prompt)])
        return {
            "proposed_changes": proposed.model_dump(),
            "approval_state": {section: ""}, # CRITICAL: Resets gate to trigger interrupt again
            "workflow_logs": [f"[Cerebras/llama3.1-8b] Generated proposal for '{section}'"]
        }
    except Exception as cerebras_error:
        print(f"[Cerebras Error] {str(cerebras_error)}")

    try:
        llm = get_llm("gemini").with_structured_output(ProposedChanges)
        proposed = llm.invoke([HumanMessage(content=prompt)])
        return {
            "proposed_changes": proposed.model_dump(),
            "approval_state": {section: ""}, # CRITICAL: Resets gate to trigger interrupt again
            "workflow_logs": [f"[Gemini fallback] Generated proposal for '{section}'"]
        }
    except Exception as e:
        return {
            "errors": [f"optimize_section_node failed: {str(e)}"],
            "approval_state": {section: ""},
            "proposed_changes": {
                "new_content": f"[AI Error] Failed to optimize '{section}'. Click Regenerate to retry.",
                "reasoning": "Providers failed. Check API keys and rate limits."
            }
        }

def approval_processing_node(state: GlobalGraphState) -> Dict[str, Any]:
    section = state.current_section or "summary"
    approval_state = state.approval_state or {}
    section_status = approval_state.get(section, "")

    if section_status == "skipped":
        return {"workflow_logs": [f"Skipped section: {section}"]}

    proposed = state.proposed_changes or {}

    # First Review or Regenerated Draft -> HITL INTERRUPT
    if section_status == "":
        interrupt({
            "type": "resume_review",
            "section": section,
            "proposal": proposed,
        })

    if section_status == "approved":
        return {"workflow_logs": [f"Approved section: {section}"]}

    # Regenerate / Reject Math (made simpler by the reducer)
    counts_dict = state.section_retry_counts or {}
    current_count = counts_dict.get(section, 0)

    return {
        "section_retry_counts": {section: current_count + 1},
        "workflow_logs": [f"Regenerating section: {section}"]
    }

def commit_changes_node(state: GlobalGraphState) -> Dict[str, Any]:
    proposed = state.proposed_changes or {}
    section = state.current_section or "summary"
    
    if state.optimized_resume:
        optimized = copy.deepcopy(state.optimized_resume)
    else:
        optimized = copy.deepcopy(state.original_resume)
    
    new_content = proposed.get("new_content")

    # Overwrite the section with AI improvements if valid. (Exports pull directly from this)
    if (new_content and isinstance(new_content, str) and not new_content.startswith("⚠️")):
        setattr(optimized, section, new_content)
        
    all_sections = ["summary", "experience", "projects", "skills"]
    try:
        current_idx = all_sections.index(section)
        next_section = all_sections[current_idx + 1]
    except (ValueError, IndexError):
        next_section = "DONE"
        
    return {
        "optimized_resume": optimized,
        "current_section": next_section,
        "proposed_changes": {}, 
        "workflow_logs": [f"Committed approved changes to {section}"]
    }