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

def _get_section_data(original_resume: Any, section: str) -> Any:
    if not original_resume:
        return None
    if isinstance(original_resume, dict):
        return original_resume.get(section)
    return getattr(original_resume, section, None)

def _is_section_empty(value: Any) -> bool:
    """Recursive deep check to catch empty lists, empty dicts, and string nulls."""
    if value is None:
        return True
    if isinstance(value, list):
        return all(_is_section_empty(item) for item in value)
    if isinstance(value, dict):
        return all(_is_section_empty(v) for v in value.values())
        
    text = str(value).strip().lower()
    if not text or text in ("none", "null", "n/a", "not provided", "missing", "empty", "[]", "{}"):
        return True
    return False

def _is_valid_proposal(proposed: ProposedChanges) -> bool:
    """Ensures the LLM didn't just return an empty string or spaces."""
    if not proposed or not proposed.new_content:
        return False
    return len(proposed.new_content.strip()) > 5

def optimize_section_node(state: GlobalGraphState) -> Dict[str, Any]:
    section = state.current_section or "summary"
    original = state.original_resume
    ats_report = state.ats_report
    
    feedback_dict = state.human_feedback or {}
    feedback_text = feedback_dict.get(section, "")
    
    raw_section = _get_section_data(original, section)

    # SMART SKIP: Gracefully and deeply skip null/empty sections without ANY API calls
    if _is_section_empty(raw_section):
        return {
            "workflow_logs": [f"Skipped optimization for missing/empty section: {section}"],
            "approval_state": {section: "skipped"},
            "proposed_changes": {"new_content": "null", "reasoning": "Section was empty."}
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
    Never return an empty string.
    """

    for provider_name in ("cerebras", "gemini"):
        try:
            llm = get_llm(provider_name).with_structured_output(ProposedChanges)
            proposed = llm.invoke([HumanMessage(content=prompt)])
            
            if not _is_valid_proposal(proposed):
                raise ValueError(f"{provider_name} returned empty new_content")
                
            return {
                "proposed_changes": proposed.model_dump(),
                "workflow_logs": [f"[{provider_name}] Generated proposal for '{section}'"]
            }
        except Exception as e:
            print(f"[optimize_section_node] {provider_name} failed for '{section}': {e}")

    # Both providers failed or returned empty — deterministic, visible fallback
    return {
        "errors": [f"optimize_section_node: both providers failed/empty for '{section}'"],
        "proposed_changes": {
            "new_content": f"⚠️ AI could not generate a proposal for '{section}'. Click Try Again, or check server logs.",
            "reasoning": "Both Cerebras and Gemini either errored or returned empty content."
        }
    }

def approval_processing_node(state: GlobalGraphState) -> Dict[str, Any]:
    section = state.current_section or "summary"
    
    approval_state = state.approval_state or {}
    if approval_state.get(section) == "skipped":
        return {"workflow_logs": [f"Auto-skipped empty section: {section}"]}

    # EXACT HITL PAYLOAD: LangGraph freezes here and embeds this dict into the interrupt object
    decision = interrupt({
        "type": "resume_review",
        "section": section,
        "proposal": state.proposed_changes or {},
    })

    action = (decision or {}).get("action")
    feedback = (decision or {}).get("feedback", "")

    if action == "skip":
        return {"approval_state": {section: "skipped"}, "workflow_logs": [f"User skipped: {section}"]}

    if action == "approve":
        return {
            "approval_state": {section: "approved"},
            "human_feedback": {section: feedback},
            "workflow_logs": [f"Approved: {section}"]
        }

    counts_dict = state.section_retry_counts or {}
    current_count = counts_dict.get(section, 0)
    return {
        "approval_state": {section: "rejected"},
        "human_feedback": {section: feedback},
        "section_retry_counts": {section: current_count + 1},
        "workflow_logs": [f"Regenerating: {section} - Attempt {current_count + 1}"]
    }

def commit_changes_node(state: GlobalGraphState) -> Dict[str, Any]:
    proposed = state.proposed_changes or {}
    section = state.current_section or "summary"
    
    optimized = copy.deepcopy(state.optimized_resume) if state.optimized_resume else copy.deepcopy(state.original_resume)
    
    new_content = proposed.get("new_content")
    status = (state.approval_state or {}).get(section, "")

    if status == "approved" and new_content and isinstance(new_content, str) and not new_content.startswith("⚠️"):
        if isinstance(optimized, dict):
            optimized[section] = new_content
        else:
            setattr(optimized, section, new_content)
        
    master_sequence = ["summary", "skills", "experience", "projects", "education", "certifications"]
    
    try:
        current_idx = master_sequence.index(section)
    except ValueError:
        current_idx = -1
        
    next_section = "DONE"
    
    # SMART FAST-FORWARD: Scan ahead and only pause on sections with actual data
    for i in range(current_idx + 1, len(master_sequence)):
        candidate = master_sequence[i]
        candidate_data = _get_section_data(state.original_resume, candidate)
        if not _is_section_empty(candidate_data):
            next_section = candidate
            break
        
    return {
        "optimized_resume": optimized,
        "current_section": next_section,
        "proposed_changes": {}, 
        "workflow_logs": [f"Committed changes for '{section}', advancing to '{next_section}'"]
    }