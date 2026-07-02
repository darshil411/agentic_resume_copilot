from app.graph.state.global_state import GlobalGraphState

def route_after_approval(state: GlobalGraphState) -> str:
    """
    Deterministic Router: Decides where to go after approval processing.
    It inspects the state variables and returns the name of the next node.
    No LLM is used here to ensure absolute predictability and safe checkpoint recovery.
    """
    # FIX 1: Use Pydantic dot-notation to get the current section and states
    section = state.current_section or "summary"
    approval_state = state.approval_state
    
    # FIX 2: Guard against None — these are Optional fields in GlobalGraphState
    status = (approval_state or {}).get(section, "")
    if status == "skipped":
        return "commit_changes_node"

    if status == "approved":
        # If approved, move to commit the changes deterministically
        return "commit_changes_node"
    
    # If rejected, check retry limits
    counts = state.section_retry_counts or {}
    current_retries = counts.get(section, 0)
    
    MAX_RETRIES = 2
    if current_retries >= MAX_RETRIES:
        # Exceeded max retries, escalate or move on
        return "escalation_node"
    
    # Otherwise, loop back to regenerate the proposal
    return "optimize_section_node"