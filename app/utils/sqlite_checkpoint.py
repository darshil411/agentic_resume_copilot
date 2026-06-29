"""
Checkpointer factory for LangGraph state persistence.

In LangGraph >= 1.x, the SQLite checkpointer was moved to the separate
`langgraph-checkpoint-sqlite` package. If that package is not installed,
we fall back to in-memory checkpointing (suitable for development).
For production, install:  pip install langgraph-checkpoint-sqlite
"""

def get_checkpointer():
    """
    Returns the best available LangGraph checkpointer.

    Priority:
      1. SqliteSaver (persistent, requires langgraph-checkpoint-sqlite)
      2. MemorySaver (in-process, no extra dependencies)
    """
    try:
        # Modern package name (langgraph >= 0.2)
        from langgraph.checkpoint.sqlite import SqliteSaver  # type: ignore
        import sqlite3, os

        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        db_path = os.path.join(root_dir, "data", "checkpoints.sqlite")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        conn = sqlite3.connect(db_path, check_same_thread=False)
        print(f"[checkpointer] Using SqliteSaver at {db_path}")
        return SqliteSaver(conn)

    except (ImportError, ModuleNotFoundError):
        pass

    try:
        # External package: pip install langgraph-checkpoint-sqlite
        from langgraph_checkpoint_sqlite import SqliteSaver  # type: ignore
        import sqlite3, os

        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        db_path = os.path.join(root_dir, "data", "checkpoints.sqlite")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        conn = sqlite3.connect(db_path, check_same_thread=False)
        print(f"[checkpointer] Using SqliteSaver (external pkg) at {db_path}")
        return SqliteSaver(conn)

    except (ImportError, ModuleNotFoundError):
        pass

    # Fallback: in-memory (state is lost on server restart, fine for dev)
    from langgraph.checkpoint.memory import MemorySaver
    print("[checkpointer] langgraph-checkpoint-sqlite not found — using MemorySaver (in-memory).")
    print("[checkpointer] Install for persistence: pip install langgraph-checkpoint-sqlite")
    return MemorySaver()
