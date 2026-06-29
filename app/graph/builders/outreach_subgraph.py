from langgraph.graph import StateGraph, END # pyright: ignore[reportMissingImports]
from app.graph.state.global_state import GlobalGraphState
from app.graph.nodes.outreach_nodes import generate_outreach_templates_node

def build_outreach_subgraph():
    # CHANGE THIS: Use GlobalGraphState instead of OutreachGraphState
    builder = StateGraph(GlobalGraphState)
    
    builder.add_node("generate_outreach_templates_node", generate_outreach_templates_node)
    
    builder.add_edge("generate_outreach_templates_node", END)
    builder.set_entry_point("generate_outreach_templates_node")
    
    return builder.compile()