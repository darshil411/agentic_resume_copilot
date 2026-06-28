from langgraph.graph import StateGraph, END
from app.graph.nodes.resume_nodes import (
    ResumeGraphState,
    optimize_section_node,
    approval_processing_node,
    commit_changes_node,
    recompute_ats_node,
    resume_export_node
)
from app.graph.routers.resume_router import route_after_approval
from app.graph.nodes.error_nodes import escalation_node

def build_resume_subgraph() -> StateGraph:
    """
    Builds the HITL Resume Optimization branch.
    Demonstrates interrupts, conditional routing, and deterministic commits.
    """
    builder = StateGraph(ResumeGraphState)
    
    # Add Nodes
    builder.add_node("optimize_section_node", optimize_section_node)
    builder.add_node("approval_processing_node", approval_processing_node)
    builder.add_node("commit_changes_node", commit_changes_node)
    builder.add_node("recompute_ats_node", recompute_ats_node)
    builder.add_node("resume_export_node", resume_export_node)
    builder.add_node("escalation_node", escalation_node)
    
    # Define Edges
    builder.set_entry_point("optimize_section_node")
    
    # To demonstrate HITL, we interrupt BEFORE the approval processing node.
    # The external caller will update the state with 'approval_state' and resume the graph.
    builder.add_edge("optimize_section_node", "approval_processing_node")
    
    builder.add_conditional_edges(
        "approval_processing_node",
        route_after_approval,
        {
            "commit_changes_node": "commit_changes_node",
            "optimize_section_node": "optimize_section_node",
            "escalation_node": "escalation_node"
        }
    )
    
    builder.add_edge("commit_changes_node", "recompute_ats_node")
    builder.add_edge("recompute_ats_node", "resume_export_node")
    
    builder.add_edge("resume_export_node", END)
    builder.add_edge("escalation_node", END)
    
    # The `interrupt_before` is key for the HITL flow. The graph execution pauses here.
    return builder.compile(interrupt_before=["approval_processing_node"])

resume_subgraph = build_resume_subgraph()
