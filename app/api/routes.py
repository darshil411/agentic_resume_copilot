import os
import shutil
import uuid
import traceback
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File, Form  # pyright: ignore[reportMissingImports]
from pydantic import BaseModel  # pyright: ignore[reportMissingImports]

from app.graph.builders.main_graph import build_main_graph
from app.utils.sqlite_checkpoint import get_checkpointer

# ── Router ───────────────────────────────────────────────────────────────────
router = APIRouter(prefix="/api/v1/workflow")

# ── Shared graph (built once at module load) ──────────────────────────────────
checkpointer = get_checkpointer()
app_graph = build_main_graph(checkpointer=checkpointer)

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
        snapshot = app_graph.get_state(config)
    except Exception as exc:
        print(f"[state] get_state error for {thread_id}: {exc}")

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
async def submit_approval(
    background_tasks: BackgroundTasks,
    request: ApprovalRequest,
):
    """
    Resumes a paused (HITL) workflow with the human's decision.
    Also runs the resumed graph in the background.
    """
    config = {"configurable": {"thread_id": request.thread_id}}
    snapshot = app_graph.get_state(config)

    if not snapshot or not snapshot.next:
        raise HTTPException(
            status_code=400, detail="Workflow is not currently awaiting approval."
        )

    # Check for approval nodes — may be subgraph-qualified e.g. "resume_subgraph:approval_processing_node"
    if not any("approval" in n for n in snapshot.next):
        raise HTTPException(
            status_code=400,
            detail=f"Workflow is paused but not at approval node. Next: {list(snapshot.next)}",
        )

    approved = request.action.lower() == "approve"

    # Inject human decision into graph state
    # Target the approval_processing_node since that's where interrupt_before is set
    app_graph.update_state(
        config,
        {
            "approval_state": {
                "approved": approved,
                "feedback": request.feedback or "",
            }
        },
        as_node="approval_processing_node",
    )

    # Resume graph in background
    _run_status[request.thread_id] = "running"

    def _resume():
        try:
            app_graph.invoke(None, config=config)
            _run_status[request.thread_id] = "done"
        except Exception as exc:
            _run_status[request.thread_id] = f"error: {exc}"
            print(f"[graph] Resume of {request.thread_id} FAILED: {exc}")

    background_tasks.add_task(_resume)

    return {
        "message": f"Action '{request.action}' submitted. Workflow resuming.",
        "thread_id": request.thread_id,
    }
