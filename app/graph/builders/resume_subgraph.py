from langgraph.graph import StateGraph, END # pyright: ignore[reportMissingImports]
from app.graph.state.global_state import GlobalGraphState
from app.graph.nodes.resume_nodes import optimize_section_node, approval_processing_node, commit_changes_node
from app.graph.nodes.error_nodes import escalation_node
from app.graph.routers.resume_router import route_after_approval

def route_after_commit(state: GlobalGraphState) -> str:
    """Checks if we are done with all sections or need to loop."""
    if state.current_section == "DONE":
        return END
    return "optimize_section_node"

def build_resume_subgraph():
    builder = StateGraph(GlobalGraphState)
    
    builder.add_node("optimize_section_node", optimize_section_node)
    builder.add_node("approval_processing_node", approval_processing_node)
    builder.add_node("commit_changes_node", commit_changes_node)
    builder.add_node("escalation_node", escalation_node)
    
    builder.add_edge("optimize_section_node", "approval_processing_node")
    
    builder.add_conditional_edges(
        "approval_processing_node",
        route_after_approval,
        {
            "commit_changes_node": "commit_changes_node",
            "optimize_section_node": "optimize_section_node",
            "escalation_node": "escalation_node",
        }
    )
    
    # FIX: Loop back to optimize the next section until DONE
    builder.add_conditional_edges(
        "commit_changes_node",
        route_after_commit,
        {
            END: END,
            "optimize_section_node": "optimize_section_node"
        }
    )
    
    builder.add_edge("escalation_node", END)
    builder.set_entry_point("optimize_section_node")
    
    return builder.compile(interrupt_before=["approval_processing_node"])