from langgraph.graph import StateGraph, START, END # pyright: ignore[reportMissingImports]
from app.graph.state.global_state import GlobalGraphState
from app.graph.nodes.foundation_nodes import (
    resume_upload_node, resume_extraction_node, resume_structuring_node,
    jd_analysis_node, ats_evaluation_node, trigger_background_workers_node
)
from app.graph.nodes.error_nodes import (
    parsing_error_node, schema_validation_retry_node, escalation_node
)
from app.graph.routers.error_router import route_on_errors
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
    
    # 2. Trigger Background Workers
    builder.add_node("trigger_background_workers_node", trigger_background_workers_node)
    
    # 3. HITL Subgraph
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
    
    # --- TRIGGER BACKGROUND & START HITL ---
    builder.add_edge("ats_evaluation_node", "trigger_background_workers_node")
    builder.add_edge("trigger_background_workers_node", "resume_subgraph")
    
    builder.add_edge("resume_subgraph", "final_dashboard_node")
    builder.add_edge("final_dashboard_node", END)
    
    # Error routes
    builder.add_edge("parsing_error_node", END)
    builder.add_edge("schema_validation_retry_node", "resume_structuring_node")
    builder.add_edge("escalation_node", END)
    
    return builder.compile(checkpointer=checkpointer)