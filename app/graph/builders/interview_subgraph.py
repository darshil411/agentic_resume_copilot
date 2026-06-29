from langgraph.graph import StateGraph, END # pyright: ignore[reportMissingImports]
from app.graph.state.global_state import GlobalGraphState
from app.graph.nodes.interview_nodes import generate_interview_prep_node

def build_interview_subgraph():
    # CHANGE THIS: Use GlobalGraphState instead of InterviewGraphState
    builder = StateGraph(GlobalGraphState)
    
    builder.add_node("generate_interview_prep_node", generate_interview_prep_node)
    
    builder.add_edge("generate_interview_prep_node", END)
    builder.set_entry_point("generate_interview_prep_node")
    
    return builder.compile()