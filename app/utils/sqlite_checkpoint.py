import os
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

def get_checkpointer(db_path: str = None) -> SqliteSaver:
    """
    Initializes and returns a SqliteSaver checkpointer for LangGraph state persistence.
    This enables pausing, interrupting, and resuming the workflow.
    """
    if not db_path:
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        db_path = os.path.join(root_dir, "data", "checkpoints.sqlite")
        
    # Ensure data directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Establish connection and return checkpointer
    conn = sqlite3.connect(db_path, check_same_thread=False)
    memory = SqliteSaver(conn)
    return memory
