from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import uuid

from app.graph.builders.main_graph import build_main_graph
from app.utils.sqlite_checkpoint import get_checkpointer

router = APIRouter()

# Instantiate the graph with the checkpointer for persistent state
checkpointer = get_checkpointer()
app_graph = build_main_graph()
# We must re-compile with the checkpointer to enable state persistence across API calls
app_graph = build_main_graph().with_config({"checkpointer": checkpointer})

class StartWorkflowRequest(BaseModel):
    resume_file_path: str
    job_description_text: str

class ApprovalRequest(BaseModel):
    thread_id: str
    approved: bool
    feedback: Optional[str] = None

@router.post("/workflow/start")
def start_workflow(request: StartWorkflowRequest):
    """
    Starts the LangGraph workflow.
    Creates a unique thread_id for checkpointing and resumability.
    """
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    initial_state = {
        "resume_file_path": request.resume_file_path,
        "job_description_text": request.job_description_text,
        "workflow_logs": [],
        "errors": []
    }
    
    # We invoke the graph. It will run until the HITL interrupt at 'approval_processing_node'
    # or until completion if it fails early.
    result = app_graph.invoke(initial_state, config=config)
    
    return {
        "thread_id": thread_id,
        "message": "Workflow started. Check status to see if it's awaiting approval.",
        "status": "RUNNING"
    }

@router.get("/workflow/{thread_id}/state")
def get_workflow_state(thread_id: str):
    """
    Fetches the current state of the workflow from the SQLite checkpointer.
    Useful for the frontend to poll status (e.g., waiting for HITL approval).
    """
    config = {"configurable": {"thread_id": thread_id}}
    state_snapshot = app_graph.get_state(config)
    
    if not state_snapshot:
        raise HTTPException(status_code=404, detail="Workflow thread not found.")
        
    return {
        "current_state": state_snapshot.values,
        "next_nodes": state_snapshot.next  # If this contains 'approval_processing_node', we are paused!
    }

@router.post("/workflow/approve")
def submit_approval(request: ApprovalRequest):
    """
    Resumes a paused workflow by injecting the human approval state.
    Demonstrates LangGraph's ability to update state and continue execution.
    """
    config = {"configurable": {"thread_id": request.thread_id}}
    state_snapshot = app_graph.get_state(config)
    
    if not state_snapshot or not state_snapshot.next:
        raise HTTPException(status_code=400, detail="Workflow is not currently awaiting approval.")
        
    if "approval_processing_node" not in state_snapshot.next:
        raise HTTPException(status_code=400, detail="Workflow is paused, but not at the approval node.")
        
    # Update the state as if it came from the node before the interrupt
    # We use 'update_state' to inject the human's decision
    app_graph.update_state(
        config,
        {"approval_state": {"approved": request.approved, "feedback": request.feedback}},
        as_node="optimize_section_node" # We pretend the optimize node provided this state
    )
    
    # Resume the graph with None (it will pick up from the updated state)
    result = app_graph.invoke(None, config=config)
    
    return {
        "message": "Approval submitted and workflow resumed.",
        "thread_id": request.thread_id
    }
