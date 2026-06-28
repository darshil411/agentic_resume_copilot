from app.graph.nodes.resume_nodes import ResumeGraphState

def route_after_approval(state: ResumeGraphState) -> str:
    """
    Deterministic Router: Decides where to go after approval processing.
    It inspects the state variables and returns the name of the next node.
    No LLM is used here to ensure absolute predictability and safe checkpoint recovery.
    """
    approval_state = state.get("approval_state", {})
    approved = approval_state.get("approved", False)
    
    if approved:
        # If approved, move to commit the changes deterministically
        return "commit_changes_node"
    
    # If rejected, check retry limits
    section = state.get("current_section", "summary")
    counts = state.get("section_retry_counts", {})
    current_retries = counts.get(section, 0)
    
    MAX_RETRIES = 2
    if current_retries >= MAX_RETRIES:
        # Exceeded max retries, escalate or move on
        return "escalation_node"
    
    # Otherwise, loop back to regenerate the proposal
    return "optimize_section_node"
