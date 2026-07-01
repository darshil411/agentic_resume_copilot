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
from fastapi import APIRouter, Request, BackgroundTasks

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
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state_snapshot = app_graph.get_state(config)
        
        # 1. Safely extract standard values from Pydantic
        if hasattr(state_snapshot.values, "model_dump"):
            values = state_snapshot.values.model_dump()
        elif hasattr(state_snapshot.values, "dict"):
            values = state_snapshot.values.dict()
        else:
            values = dict(state_snapshot.values)
            
        # 2. Gather ALL next_nodes (Parent + deeply nested Subgraphs)
        all_next_nodes = list(state_snapshot.next) if state_snapshot.next else []
        
        if hasattr(state_snapshot, 'tasks') and state_snapshot.tasks:
            for task in state_snapshot.tasks:
                task_state = getattr(task, 'state', None)
                if not task_state:
                    continue
                    
                # Extract deeper next_nodes to successfully spot the HITL pause
                if hasattr(task_state, 'next') and task_state.next:
                    all_next_nodes.extend(task_state.next)
                    
                # Extract deeper subgraph values
                task_values = task_state if isinstance(task_state, dict) else getattr(task_state, 'values', {})
                if isinstance(task_values, dict):
                    if task_values.get("proposed_changes"):
                        values["proposed_changes"] = task_values.get("proposed_changes")
                    if task_values.get("current_section"):
                        values["current_section"] = task_values.get("current_section")
                        
        # 3. Determine true status based on the combined next_nodes list
        run_status = _run_status.get(thread_id, "running")
        
        if "approval_processing_node" in all_next_nodes:
            current_state = "interrupt"
        elif run_status.startswith("error"):
            current_state = "error"
        elif not all_next_nodes and run_status == "done":
            current_state = "end"
        else:
            current_state = "running"
            
        return {
            "state": current_state,
            "next_nodes": all_next_nodes,
            "values": values
        }
    except Exception as e:
        print(f"API GET STATE ERROR: {e}")  
        return {"error": str(e), "state": "error"}

@router.post("/approve")
async def submit_approval(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    thread_id = data.get("thread_id")
    approved = data.get("approved")
    feedback = data.get("feedback", "")
    
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        state_snapshot = app_graph.get_state(config)
        target_config = config
        
        # CORE FIX: Find the SPECIFIC subgraph that is actively paused
        if hasattr(state_snapshot, 'tasks') and state_snapshot.tasks:
            for task in state_snapshot.tasks:
                task_state = getattr(task, 'state', None)
                # ONLY grab the config if this task has a pending 'next' node (Meaning it is the paused one!)
                if task_state and hasattr(task_state, 'next') and task_state.next:
                    if hasattr(task_state, 'config'):
                        target_config = task_state.config
                        break
                        
        # Extract state dict safely using the correct config
        raw_values = app_graph.get_state(target_config).values
        if hasattr(raw_values, "model_dump"):
            current_state = raw_values.model_dump()
        elif hasattr(raw_values, "dict"):
            current_state = raw_values.dict()
        else:
            current_state = dict(raw_values)
        
        current_section = current_state.get("current_section") or "summary"
        status_str = "approved" if approved else "rejected"
        
        new_approval_state = current_state.get("approval_state") or {}
        new_approval_state[current_section] = status_str
        
        new_feedback_state = current_state.get("human_feedback") or {}
        new_feedback_state[current_section] = feedback
        
        app_graph.update_state(
            target_config,
            {
                "approval_state": new_approval_state,
                "human_feedback": new_feedback_state
            }
        )
        
        background_tasks.add_task(_resume_graph_background, thread_id)
        return {"message": "Approval submitted and workflow resumed."}
    except Exception as e:
        print(f"API APPROVAL ERROR: {e}")  
        return {"error": str(e)}