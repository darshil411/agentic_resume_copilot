from .state import GraphState

MAX_RETRIES = 3

def approval_router(state: GraphState):
    status = state.approval_status.get(state.current_section)

    if status == "approved":
        return "commit_changes_node"

    # If not approved, handle retry routing natively here
    current = state.current_section
    retries = state.retry_counts.get(current, 0)

    if retries >= MAX_RETRIES:
        return "__end__"

    return "optimize_projects_node"