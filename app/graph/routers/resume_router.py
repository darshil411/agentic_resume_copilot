from app.graph.state.global_state import GlobalGraphState

def route_after_approval(state: GlobalGraphState) -> str:
    section = state.current_section or "summary"
    
    # Safely pull the status from the dictionary
    approval_dict = state.approval_state or {}
    status = approval_dict.get(section, "")

    if status in ("approved", "skipped"):
        return "commit_changes_node"

    # Safely pull retry counts
    counts_dict = state.section_retry_counts or {}
    if counts_dict.get(section, 0) >= 2:
        return "escalation_node"

    return "optimize_section_node"