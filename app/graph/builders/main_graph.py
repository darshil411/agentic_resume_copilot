from langgraph.graph import StateGraph, START, END # pyright: ignore[reportMissingImports]
from app.graph.state.global_state import GlobalGraphState
from app.graph.nodes.foundation_nodes import (
    resume_upload_node, resume_extraction_node, resume_structuring_node,
    jd_analysis_node, ats_evaluation_node
)
from app.graph.nodes.error_nodes import (
    parsing_error_node, schema_validation_retry_node, escalation_node
)
from app.graph.routers.error_router import route_on_errors
from app.graph.nodes.interview_nodes import generate_interview_prep_node
from app.graph.nodes.outreach_nodes import generate_outreach_templates_node
from app.graph.builders.resume_subgraph import build_resume_subgraph

def build_main_graph(checkpointer=None) -> StateGraph:
    builder = StateGraph(GlobalGraphState)
    
    # 1. Foundation Nodes
    builder.add_node("resume_upload_node", resume_upload_node)
    builder.add_node("resume_extraction_node", resume_extraction_node)
    builder.add_node("resume_structuring_node", resume_structuring_node)
    builder.add_node("jd_analysis_node", jd_analysis_node)
    builder.add_node("ats_evaluation_node", ats_evaluation_node)
    
    # Error Nodes
    builder.add_node("parsing_error_node", parsing_error_node)
    builder.add_node("schema_validation_retry_node", schema_validation_retry_node)
    builder.add_node("escalation_node", escalation_node)
    
    # 2. Parallel AI Nodes (Offloaded to Groq!)
    builder.add_node("outreach_node", generate_outreach_templates_node)
    builder.add_node("interview_node", generate_interview_prep_node)
    
    # 3. Join Node (Traffic Light: Waits for parallel branches to finish)
    def join_parallel_node(state: GlobalGraphState):
        return {"workflow_logs": ["Outreach and Interview ready. Starting Resume Optimization."]}
    builder.add_node("join_parallel_node", join_parallel_node)
    
    # 4. HITL Subgraph
    resume_app = build_resume_subgraph()
    builder.add_node("resume_subgraph", resume_app)
    
    def final_dashboard_node(state: GlobalGraphState):
        return {"workflow_logs": ["All workflow steps completed successfully."]}
    builder.add_node("final_dashboard_node", final_dashboard_node)
    
    # --- EDGES ---
    builder.set_entry_point("resume_upload_node")
    builder.add_edge("resume_upload_node", "resume_extraction_node")
    
    builder.add_conditional_edges("resume_extraction_node", route_on_errors, {
        "continue": "resume_structuring_node",
        "parsing_error_node": "parsing_error_node", "escalation_node": "escalation_node"
    })
    builder.add_conditional_edges("resume_structuring_node", route_on_errors, {
        "continue": "jd_analysis_node",
        "schema_validation_retry_node": "schema_validation_retry_node", "escalation_node": "escalation_node"
    })
    builder.add_edge("jd_analysis_node", "ats_evaluation_node")
    
    # --- TRUE PARALLEL FAN-OUT ---
    builder.add_edge("ats_evaluation_node", "outreach_node")
    builder.add_edge("ats_evaluation_node", "interview_node")
    
    # --- SYNCHRONIZED FAN-IN ---
    builder.add_edge("outreach_node", "join_parallel_node")
    builder.add_edge("interview_node", "join_parallel_node")
    
    # --- START HITL ONLY AFTER PARALLEL COMPLETES ---
    builder.add_edge("join_parallel_node", "resume_subgraph")
    builder.add_edge("resume_subgraph", "final_dashboard_node")
    builder.add_edge("final_dashboard_node", END)
    
    # Error routes
    builder.add_edge("parsing_error_node", END)
    builder.add_edge("schema_validation_retry_node", "resume_structuring_node")
    builder.add_edge("escalation_node", END)
    
    return builder.compile(checkpointer=checkpointer)