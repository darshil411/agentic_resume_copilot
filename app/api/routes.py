import os
import shutil
import uuid
import traceback
import asyncio
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File, Form, Request  # pyright: ignore[reportMissingImports]
from pydantic import BaseModel  # pyright: ignore[reportMissingImports]

from app.graph.builders.main_graph import build_main_graph
from app.utils.sqlite_checkpoint import get_checkpointer

# ── Router ───────────────────────────────────────────────────────────────────
router = APIRouter(prefix="/api/v1/workflow")

# ── Shared graph (built once at module load) ──────────────────────────────────
checkpointer = get_checkpointer()
app_graph = build_main_graph(checkpointer=checkpointer)

# ── Thread pool for running synchronous graph operations off the event loop ──
_executor = ThreadPoolExecutor(max_workers=4)

# ── Uploads directory ─────────────────────────────────────────────────────────
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOADS_DIR = os.path.join(ROOT_DIR, "data", "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

# ── In-memory run-status store (thread_id → status/error string) ─────────────
# Lets the frontend distinguish "still running" from "graph crashed".
_run_status: dict[str, str] = {}   # "running" | "done" | "error: <msg>"


# ── Request models ─────────────────────────────────────────────────────────────
class ApprovalRequest(BaseModel):
    thread_id: str
    action: str           # "approve" or "regenerate"
    feedback: Optional[str] = None


# ── Background graph runner ───────────────────────────────────────────────────
def _run_graph_background(thread_id: str, initial_state: dict) -> None:
    """
    Executes the LangGraph workflow in a background thread.
    Stores the outcome in _run_status so the /state endpoint can reflect it.
    """
    config = {"configurable": {"thread_id": thread_id}}
    try:
        print(f"[graph] Starting thread {thread_id}")
        app_graph.invoke(initial_state, config=config)
        _run_status[thread_id] = "done"
        print(f"[graph] Thread {thread_id} completed.")
    except Exception as exc:
        err_msg = f"error: {exc}"
        _run_status[thread_id] = err_msg
        print(f"[graph] Thread {thread_id} FAILED:\n{traceback.format_exc()}")


def _resume_graph_background(thread_id: str) -> None:
    """
    Resumes a paused LangGraph workflow (after HITL approval) in a background thread.
    """
    config = {"configurable": {"thread_id": thread_id}}
    try:
        print(f"[graph] Resuming thread {thread_id}")
        _run_status[thread_id] = "running"
        app_graph.invoke(None, config=config)
        _run_status[thread_id] = "done"
        print(f"[graph] Thread {thread_id} resumed and completed.")
    except Exception as exc:
        err_msg = f"error: {exc}"
        _run_status[thread_id] = err_msg
        print(f"[graph] Thread {thread_id} FAILED on resume:\n{traceback.format_exc()}")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/start")
async def start_workflow(
    background_tasks: BackgroundTasks,
    resume: UploadFile = File(..., description="PDF resume file"),
    job_description: str = Form(..., description="Job description text"),
):
    """
    Saves the uploaded PDF, creates a thread, launches the LangGraph workflow
    as a background task, and returns the thread_id IMMEDIATELY so the
    browser can redirect to the dashboard without waiting for LLM calls.
    """
    # 1. Save PDF to disk
    file_ext = os.path.splitext(resume.filename or "resume")[1] or ".pdf"
    saved_filename = f"{uuid.uuid4()}{file_ext}"
    saved_path = os.path.join(UPLOADS_DIR, saved_filename)

    with open(saved_path, "wb") as f:
        shutil.copyfileobj(resume.file, f)

    # 2. Create unique thread
    thread_id = str(uuid.uuid4())
    _run_status[thread_id] = "running"

    initial_state = {
        "resume_file_path": saved_path,
        "job_description_text": job_description,
        "workflow_logs": [],
        "errors": [],
        "current_section": "summary",   # FIX: seed the section so the subgraph knows what to optimize
    }

    # 3. Schedule graph to run in the background — return immediately
    background_tasks.add_task(_run_graph_background, thread_id, initial_state)

    return {
        "thread_id": thread_id,
        "message": "Workflow started. Poll /state to track progress.",
        "status": "RUNNING",
    }


@router.get("/{thread_id}/state")
async def get_workflow_state(thread_id: str):
    """
    Returns the current graph state for a given thread.

    Response shape (matches workflow.js):
      { state: "running"|"interrupt"|"end"|"error", values: {...}, next_nodes: [...] }
    """
    config = {"configurable": {"thread_id": thread_id}}

    # Check in-memory run status first (handles "not started yet" or crashed)
    run_st = _run_status.get(thread_id, "unknown")

    snapshot = None
    try:
        loop = asyncio.get_event_loop()
        # subgraphs=True allows us to see inside the paused resume_subgraph!
        snapshot = await loop.run_in_executor(_executor, lambda: app_graph.get_state(config, subgraphs=True))
    except Exception as exc:
        print(f"[state] get_state error for {thread_id}: {exc}")
        return {"state": "error", "error_message": str(exc)}

    if not snapshot:
        return {"state": "unknown", "values": {}, "next_nodes": []}

    values = snapshot.values.copy()

    # THE MAGIC FIX: Extract trapped state from the paused subgraph
    if hasattr(snapshot, "tasks"):
        for task in snapshot.tasks:
            if hasattr(task, "state") and task.state and hasattr(task.state, "values"):
                # Merge the subgraph's proposed_changes into the payload we send to the UI
                values.update(task.state.values)

    state_type = "running"

    # If graph crashed before writing any checkpoint
    if run_st.startswith("error"):
        return {
            "state": "error",
            "error_message": run_st.removeprefix("error: "),
            "values": {},
            "next_nodes": [],
        }

    # If snapshot is not yet available (graph is still starting up)
    if not snapshot or not snapshot.values:
        return {
            "state": "running",
            "values": {},
            "next_nodes": [],
        }

    next_nodes: list = list(snapshot.next) if snapshot.next else []

    # Determine high-level state string
    # NOTE: When interrupted inside a subgraph, LangGraph reports next_nodes as
    # "<subgraph_name>:<node_name>" (e.g. "resume_subgraph:approval_processing_node")
    is_interrupted = any(
        "approval" in n or "human" in n
        for n in next_nodes
    )

    if not next_nodes and run_st == "done":
        state_str = "end"
    elif next_nodes and run_st == "done":
        # Graph execution yielded back to us but there are still next nodes -> it is suspended/interrupted
        state_str = "interrupt"
    elif not next_nodes and run_st == "running":
        # Graph may be mid-execution between checkpoints
        state_str = "running"
    elif is_interrupted:
        state_str = "interrupt"
    else:
        state_str = "running"

    # Serialize Pydantic models so they are JSON-safe
    raw_values: dict = dict(snapshot.values)
    safe_values: dict = {}
    for k, v in raw_values.items():
        try:
            safe_values[k] = v.model_dump() if hasattr(v, "model_dump") else v
        except Exception:
            safe_values[k] = str(v)

    return {
        "state": state_str,
        "values": safe_values,
        "next_nodes": next_nodes,
    }


@router.post("/approve")
async def submit_approval(background_tasks: BackgroundTasks, request: Request):
    """
    Accepts human approval, finds the isolated subgraph state, updates it,
    and resumes the graph in a background thread.
    """
    data = await request.json()
    thread_id = data.get("thread_id")
    
    # 1. FIX: Correctly read the boolean 'approved' flag sent by your api.js
    approved_bool = data.get("approved")          
    status_str = "approved" if approved_bool is True else "rejected"
    feedback = data.get("feedback", "")

    if not thread_id:
        raise HTTPException(status_code=400, detail="thread_id is required")

    config = {"configurable": {"thread_id": thread_id}}

    # 2. Fetch the state, EXPLICITLY asking to see inside subgraphs
    loop = asyncio.get_event_loop()
    snapshot = await loop.run_in_executor(
        _executor, lambda: app_graph.get_state(config, subgraphs=True)
    )
    
    target_config = config # Default to parent config
    current_state = snapshot.values if snapshot else {}
    
    # 3. THE MAGIC FIX: Find the paused Subgraph's specific ID
    # We must inject the approval directly into the subgraph's isolated memory bubble.
    if snapshot and hasattr(snapshot, "tasks"):
        for task in snapshot.tasks:
            if task.name == "resume_subgraph" and hasattr(task, "state"):
                target_config = task.state.config  # <--- Get the Subgraph's private ID
                current_state = task.state.values
                break

    current_section = current_state.get("current_section", "summary")

    new_approval_state = dict(current_state.get("approval_state") or {})
    new_approval_state[current_section] = status_str

    new_feedback_state = dict(current_state.get("human_feedback") or {})
    new_feedback_state[current_section] = feedback or ""

    # 4. Push updated state back to the SUBGRAPH
    await loop.run_in_executor(
        _executor,
        lambda: app_graph.update_state(
            target_config,
            {
                "approval_state": new_approval_state,
                "human_feedback": new_feedback_state,
            }
        )
    )

    # 5. Resume the graph as a background task
    background_tasks.add_task(_resume_graph_background, thread_id)

    return {"message": "Approval submitted.", "section": current_section, "status": status_str}