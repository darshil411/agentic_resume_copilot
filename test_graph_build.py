"""Quick sanity check: builds the entire graph and prints its nodes."""
from app.graph.builders.main_graph import build_main_graph
from app.utils.sqlite_checkpoint import get_checkpointer

cp = get_checkpointer()
g = build_main_graph(checkpointer=cp)
print("Graph built OK")
print("Graph nodes:", list(g.nodes.keys()))
