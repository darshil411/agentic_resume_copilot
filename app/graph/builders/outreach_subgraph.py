from langgraph.graph import StateGraph, END
from app.graph.state.global_state import GlobalGraphState
from app.graph.nodes.outreach_nodes import generate_outreach_node

def build_outreach_subgraph() -> StateGraph:
    """
    Builds the independent outreach generation branch.
    Depends only on the original_resume and jd_analysis.
    Uses GlobalGraphState so outputs are written back to the parent graph's channels.
    """
    builder = StateGraph(GlobalGraphState)
    
    # Add Nodes
    builder.add_node("generate_outreach_node", generate_outreach_node)
    
    # Edges
    builder.set_entry_point("generate_outreach_node")
    builder.add_edge("generate_outreach_node", END)
    
    return builder.compile()
