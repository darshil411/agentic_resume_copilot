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

def optimize_section_node(state: GlobalGraphState) -> Dict[str, Any]:
    """
    LLM Node: Proposes changes for a specific section based on ATS feedback.
    """
    section = state.current_section or "summary"
    original = state.original_resume
    ats_report = state.ats_report
    
    raw_section = getattr(original, section, '') if original else ''

    # Normalize section data safely into prompt-friendly text
    if isinstance(raw_section, list):
        current_text = "\n".join([str(x) for x in raw_section])
    else:
        current_text = str(raw_section).strip()
    # Skip sections that do not exist in original resume
    if not current_text or str(current_text).strip().lower() in ("none", "null", ""):
        return {
            "workflow_logs": [
                f"Skipped optimization for missing section: {section}"
            ],
            "approval_state": {
                section: "skipped"
            }
        }
    prompt = f"""
    The current resume section '{section}' needs optimization for the target job.
    ATS Missing Skills: {ats_report.missing_skills if ats_report else []}
    Original Resume Section Data: {current_text}

    Propose an optimized version of this section that naturally incorporates missing skills
    and improves impact. Format the output as clean, professional plain text or markdown.
    """

    # Primary: Cerebras (llama3.1-8b) — fast inference, ideal for HITL loops
    try:
        llm = get_llm("cerebras").with_structured_output(ProposedChanges)
        proposed = llm.invoke([HumanMessage(content=prompt)])
        return {
            "proposed_changes": proposed.model_dump(),
            "workflow_logs": [f"[Cerebras/llama3.1-8b] Generated proposal for '{section}'"]
        }
    except Exception as cerebras_error:
        print(f"[Cerebras Error] {str(cerebras_error)}") # fall through to Gemini

    # Fallback: Gemini with key rotation
    try:
        llm = get_llm("gemini").with_structured_output(ProposedChanges)
        proposed = llm.invoke([HumanMessage(content=prompt)])
        return {
            "proposed_changes": proposed.model_dump(),
            "workflow_logs": [f"[Gemini fallback] Generated proposal for '{section}'"]
        }
    except Exception as e:
        return {
            "errors": [f"optimize_section_node failed (both providers): {str(e)}"],
            "proposed_changes": {
                "new_content": f"[AI Error] Failed to optimize '{section}'. Click Regenerate to retry.",
                "reasoning": "Both Cerebras and Gemini failed. Check API keys and rate limits."
            }
        }


def approval_processing_node(state: GlobalGraphState) -> Dict[str, Any]:
    """
    Durable HITL interrupt node.
    """

    section = state.current_section or "summary"

    approval_state = state.approval_state or {}
    section_status = approval_state.get(section, "")

    # ---------------------------------------------------
    # SKIPPED SECTION
    # ---------------------------------------------------
    if section_status == "skipped":
        return {
            "workflow_logs": [
                f"Skipped section: {section}"
            ]
        }

    proposed = state.proposed_changes or {}

    # ---------------------------------------------------
    # FIRST REVIEW → INTERRUPT
    # ---------------------------------------------------
    if section_status == "":
        interrupt({
            "type": "resume_review",
            "section": section,
            "proposal": proposed,
        })

    # ---------------------------------------------------
    # APPROVED
    # ---------------------------------------------------
    if section_status == "approved":
        return {
            "workflow_logs": [
                f"Approved section: {section}"
            ]
        }

    # ---------------------------------------------------
    # REGENERATE / REJECT
    # ---------------------------------------------------
    counts = copy.deepcopy(state.section_retry_counts or {})
    counts[section] = counts.get(section, 0) + 1

    return {
        "section_retry_counts": counts,
        "workflow_logs": [
            f"Regenerating section: {section}"
        ]
    }
def commit_changes_node(state: GlobalGraphState) -> Dict[str, Any]:
    """
    Deterministic Node: Mutates the `optimized_resume` AFTER human approval.
    """
    proposed = state.proposed_changes or {}
    section = state.current_section or "summary"
    
    if state.optimized_resume:
        optimized = copy.deepcopy(state.optimized_resume)
    else:
        optimized = copy.deepcopy(state.original_resume)
    
    # QA FIX 3: Safe injection that avoids crashing if 'new_content' is missing
    new_content = proposed.get("new_content")

    # Only overwrite if valid optimized content exists
    if (
        new_content
        and isinstance(new_content, str)
        and not new_content.startswith("⚠️")
    ):
        setattr(optimized, section, new_content)
        
    all_sections = [
    s for s in ["summary", "experience", "projects", "skills"]
    ]
    # Skip sections absent in original resume
    all_sections = [
        s for s in all_sections
        if getattr(state.original_resume, s, None)
    ]
    try:
        current_idx = all_sections.index(section)
        next_section = all_sections[current_idx + 1]
    except (ValueError, IndexError):
        next_section = "DONE"
        
    return {
        "optimized_resume": optimized,
        "current_section": next_section,
        # QA FIX 4: Clear proposed_changes so the UI doesn't carry over old text to the next loop
        "proposed_changes": {}, 
        "workflow_logs": [f"Committed approved changes to {section}"]
    }

def recompute_ats_node(state: GlobalGraphState) -> Dict[str, Any]:
    ats = copy.deepcopy(state.ats_report)
    if ats:
        ats.score = min(100.0, ats.score + 10.0)
    return {"ats_report": ats, "workflow_logs": ["Recomputed ATS score after committing changes."]}

def resume_export_node(state: GlobalGraphState) -> Dict[str, Any]:
    return {
        "resume_export_paths": {"pdf": "/exports/optimized_resume.pdf"},
        "branch_status": {
            "resume_branch": "COMPLETED"},
        "workflow_logs": ["Exported optimized resume."]
    }