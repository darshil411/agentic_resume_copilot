from langgraph.graph import StateGraph, START, END
from app.graph.state.global_state import GlobalGraphState
from app.graph.nodes.foundation_nodes import (
    resume_upload_node,
    resume_extraction_node,
    resume_structuring_node,
    jd_analysis_node,
    ats_evaluation_node
)
from app.graph.nodes.error_nodes import (
    parsing_error_node,
    schema_validation_retry_node,
    escalation_node
)
from app.graph.routers.error_router import route_on_errors
from app.graph.builders.resume_subgraph import build_resume_subgraph
from app.graph.builders.interview_subgraph import build_interview_subgraph
from app.graph.builders.outreach_subgraph import build_outreach_subgraph

def build_main_graph() -> StateGraph:
    """
    Builds the main orchestration DAG.
    Demonstrates sequential foundation nodes followed by parallel fan-out to subgraphs.
    """
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
    
    # 2. Subgraphs
    resume_app = build_resume_subgraph()
    interview_app = build_interview_subgraph()
    outreach_app = build_outreach_subgraph()
    
    # Add Subgraphs as nodes
    builder.add_node("resume_subgraph", resume_app)
    builder.add_node("interview_subgraph", interview_app)
    builder.add_node("outreach_subgraph", outreach_app)
    
    # A dummy join node to wait for parallel branches
    def join_node(state: GlobalGraphState):
        return {"workflow_logs": ["All relevant branches completed."]}
        
    builder.add_node("final_dashboard_node", join_node)
    
    # 3. Define Edges
    builder.set_entry_point("resume_upload_node")
    builder.add_edge("resume_upload_node", "resume_extraction_node")
    
    # Error checking after extraction
    builder.add_conditional_edges(
        "resume_extraction_node",
        route_on_errors,
        {
            "continue": "resume_structuring_node",
            "parsing_error_node": "parsing_error_node",
            "escalation_node": "escalation_node"
        }
    )
    
    # Error checking after structuring
    builder.add_conditional_edges(
        "resume_structuring_node",
        route_on_errors,
        {
            "continue": "jd_analysis_node",
            "schema_validation_retry_node": "schema_validation_retry_node",
            "escalation_node": "escalation_node"
        }
    )
    
    builder.add_edge("jd_analysis_node", "ats_evaluation_node")
    
    # FAN-OUT: After ATS, launch 3 branches in parallel
    builder.add_edge("ats_evaluation_node", "resume_subgraph")
    builder.add_edge("ats_evaluation_node", "interview_subgraph")
    builder.add_edge("ats_evaluation_node", "outreach_subgraph")
    
    # FAN-IN (Join)
    builder.add_edge("resume_subgraph", "final_dashboard_node")
    builder.add_edge("interview_subgraph", "final_dashboard_node")
    builder.add_edge("outreach_subgraph", "final_dashboard_node")
    
    builder.add_edge("final_dashboard_node", END)
    
    # Error edges
    builder.add_edge("parsing_error_node", END)
    builder.add_edge("schema_validation_retry_node", "resume_structuring_node")
    builder.add_edge("escalation_node", END)
    
    return builder.compile()

# This is the compiled graph that will be run with the checkpointer
# It will be instantiated in the API or runner script
