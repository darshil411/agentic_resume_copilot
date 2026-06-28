from langgraph.graph import StateGraph, END
from app.graph.state.global_state import GlobalGraphState
from app.graph.nodes.interview_nodes import InterviewGraphState, generate_interview_prep_node

def build_interview_subgraph() -> StateGraph:
    """
    Builds the independent interview preparation branch.
    Depends only on the original_resume and jd_analysis.
    """
    builder = StateGraph(InterviewGraphState)
    
    # Add Nodes
    builder.add_node("generate_interview_prep_node", generate_interview_prep_node)
    
    # Edges
    builder.set_entry_point("generate_interview_prep_node")
    builder.add_edge("generate_interview_prep_node", END)
    
    return builder.compile()

interview_subgraph = build_interview_subgraph()
