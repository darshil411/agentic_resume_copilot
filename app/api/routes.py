import os
import shutil
import uuid
import traceback
from typing import Optional, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File, Form, Request
from pydantic import BaseModel

from app.graph.builders.main_graph import build_main_graph
from app.utils.sqlite_checkpoint import get_checkpointer

from app.api.dtos.enums import WorkflowStatus
from app.api.dtos.workflow_dto import WorkflowMetadataDTO, BranchStatuses
from app.api.dtos.review_task_dto import ReviewTaskDTO
from app.api.dtos.interview_dto import InterviewDeckDTO, InterviewQuestionDTO
from app.api.dtos.outreach_dto import OutreachWorkspaceDTO, OutreachCardDTO

router = APIRouter(prefix="/api/v1")

checkpointer = get_checkpointer()
app_graph = build_main_graph(checkpointer=checkpointer)
_executor = ThreadPoolExecutor(max_workers=4)

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOADS_DIR = os.path.join(ROOT_DIR, "data", "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

_run_status: dict[str, str] = {}
_workflow_creation_times: dict[str, datetime] = {}
# Simulate versions for task items (thread_id -> section -> version)
_task_versions: dict[str, dict[str, int]] = {}

def _get_run_status(thread_id: str) -> WorkflowStatus:
    status = _run_status.get(thread_id, "running")
    if status.startswith("error"):
        return WorkflowStatus.FAILED
    if status == "done":
        return WorkflowStatus.COMPLETED
    return WorkflowStatus.PROCESSING

def _run_graph_background(thread_id: str, initial_state: dict) -> None:
    config = {"configurable": {"thread_id": thread_id}}
    try:
        app_graph.invoke(initial_state, config=config)
        _run_status[thread_id] = "done"
    except Exception as exc:
        _run_status[thread_id] = f"error: {exc}"

def _resume_graph_background(thread_id: str) -> None:
    config = {"configurable": {"thread_id": thread_id}}
    try:
        _run_status[thread_id] = "running"
        app_graph.invoke(None, config=config)
        _run_status[thread_id] = "done"
    except Exception as exc:
        _run_status[thread_id] = f"error: {exc}"

def _extract_state(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    state_snapshot = app_graph.get_state(config)
    
    # 1. Safely extract standard values from Pydantic
    if hasattr(state_snapshot.values, "model_dump"):
        values = state_snapshot.values.model_dump()
    elif hasattr(state_snapshot.values, "dict"):
        values = state_snapshot.values.dict()
    else:
        values = dict(state_snapshot.values) if state_snapshot.values else {}
        
    all_next_nodes = list(state_snapshot.next) if state_snapshot.next else []
    target_config = config
    
    if hasattr(state_snapshot, 'tasks') and state_snapshot.tasks:
        for task in state_snapshot.tasks:
            task_state = getattr(task, 'state', None)
            if not task_state: continue
            
            if hasattr(task_state, 'next') and task_state.next:
                all_next_nodes.extend(task_state.next)
                if hasattr(task_state, 'config'):
                    target_config = task_state.config
                
            task_values = task_state if isinstance(task_state, dict) else getattr(task_state, 'values', {})
            if isinstance(task_values, dict):
                if task_values.get("proposed_changes"):
                    values["proposed_changes"] = task_values.get("proposed_changes")
                if task_values.get("current_section"):
                    values["current_section"] = task_values.get("current_section")
                    
    return values, all_next_nodes, target_config


@router.post("/workflow/start")
async def start_workflow(
    background_tasks: BackgroundTasks,
    resume: UploadFile = File(...),
    job_description: str = Form(...),
):
    file_ext = os.path.splitext(resume.filename or "resume")[1] or ".pdf"
    saved_filename = f"{uuid.uuid4()}{file_ext}"
    saved_path = os.path.join(UPLOADS_DIR, saved_filename)

    with open(saved_path, "wb") as f:
        shutil.copyfileobj(resume.file, f)

    thread_id = str(uuid.uuid4())
    _run_status[thread_id] = "running"
    _workflow_creation_times[thread_id] = datetime.now()
    _task_versions[thread_id] = {}

    initial_state = {
        "resume_file_path": saved_path,
        "job_description_text": job_description,
        "workflow_logs": [],
        "errors": [],
        "current_section": "summary",
        "branch_status": {}
    }

    background_tasks.add_task(_run_graph_background, thread_id, initial_state)

    return {"thread_id": thread_id, "status": "RUNNING"}


@router.get("/workflow/{thread_id}", response_model=WorkflowMetadataDTO)
async def get_workflow_metadata(thread_id: str):
    values, all_next_nodes, _ = _extract_state(thread_id)
    overall_status = _get_run_status(thread_id)
    
    if "approval_processing_node" in all_next_nodes:
        overall_status = WorkflowStatus.ACTION_REQUIRED
        
    branch_status_dict = values.get("branch_status", {})
    
    # Fill defaults if missing
    def _parse_branch(b_name: str) -> WorkflowStatus:
        s = branch_status_dict.get(b_name)
        if isinstance(s, WorkflowStatus): return s
        if s:
            try: return WorkflowStatus(s)
            except ValueError: return WorkflowStatus.PROCESSING
        return overall_status if overall_status != WorkflowStatus.ACTION_REQUIRED else WorkflowStatus.PROCESSING

    # Specifically handle resume branch interruption
    r_branch = _parse_branch("resume_branch")
    if "approval_processing_node" in all_next_nodes:
        r_branch = WorkflowStatus.ACTION_REQUIRED
        
    branches = BranchStatuses(
        resume_branch=r_branch,
        interview_branch=_parse_branch("interview_branch"),
        outreach_branch=_parse_branch("outreach_branch")
    )
    
    return WorkflowMetadataDTO(
        thread_id=thread_id,
        created_at=_workflow_creation_times.get(thread_id, datetime.now()),
        overall_status=overall_status,
        active_branches=branches,
        current_review_section=values.get("current_section"),
        completed_sections=[] # We don't track explicitly in global state yet
    )

@router.get("/resume/task/current/{thread_id}", response_model=ReviewTaskDTO)
async def get_current_resume_task(thread_id: str):
    values, all_next_nodes, _ = _extract_state(thread_id)
    
    section = values.get("current_section", "summary")
    status = WorkflowStatus.ACTION_REQUIRED if "approval_processing_node" in all_next_nodes else _get_run_status(thread_id)
    
    if thread_id not in _task_versions:
        _task_versions[thread_id] = {}
    if section not in _task_versions[thread_id]:
        _task_versions[thread_id][section] = 1
        
    proposal = values.get("proposed_changes", {})
    original = values.get("original_resume", {})
    
    return ReviewTaskDTO(
        task_id=f"task_{thread_id}_{section}",
        version=_task_versions[thread_id][section],
        task_type="resume_section_review",
        section=section,
        status=status,
        created_at=datetime.now(),
        proposal=proposal.get("new_content", "") if isinstance(proposal, dict) else proposal,
        original=original,
        optimization_notes=proposal.get("reasoning", "") if isinstance(proposal, dict) else "",
        proposal_history=[] # Simple history stub for now
    )


class TaskApprovalRequest(BaseModel):
    task_id: str
    version: int
    feedback: str = ""

@router.post("/resume/task/approve/{thread_id}")
async def approve_resume_task(thread_id: str, request: TaskApprovalRequest, background_tasks: BackgroundTasks):
    values, all_next_nodes, target_config = _extract_state(thread_id)
    section = values.get("current_section", "summary")
    
    if "approval_processing_node" not in all_next_nodes:
        raise HTTPException(status_code=409, detail="Task not in ACTION_REQUIRED state")
        
    current_ver = _task_versions.get(thread_id, {}).get(section, 1)
    if request.version != current_ver:
        raise HTTPException(status_code=409, detail="Task version mismatch")
        
    new_approval_state = values.get("approval_state") or {}
    new_approval_state[section] = "approved"
    
    new_feedback_state = values.get("human_feedback") or {}
    new_feedback_state[section] = request.feedback
    
    app_graph.update_state(
        target_config,
        {
            "approval_state": new_approval_state,
            "human_feedback": new_feedback_state
        }
    )
    
    background_tasks.add_task(_resume_graph_background, thread_id)
    return {"status": "success"}

@router.post("/resume/task/regenerate/{thread_id}")
async def regenerate_resume_task(thread_id: str, request: TaskApprovalRequest, background_tasks: BackgroundTasks):
    values, all_next_nodes, target_config = _extract_state(thread_id)
    section = values.get("current_section", "summary")
    
    if "approval_processing_node" not in all_next_nodes:
        raise HTTPException(status_code=409, detail="Task not in ACTION_REQUIRED state")
        
    current_ver = _task_versions.get(thread_id, {}).get(section, 1)
    if request.version != current_ver:
        raise HTTPException(status_code=409, detail="Task version mismatch")
        
    _task_versions[thread_id][section] = current_ver + 1
        
    new_approval_state = values.get("approval_state") or {}
    new_approval_state[section] = "rejected"
    
    new_feedback_state = values.get("human_feedback") or {}
    new_feedback_state[section] = request.feedback
    
    app_graph.update_state(
        target_config,
        {
            "approval_state": new_approval_state,
            "human_feedback": new_feedback_state
        }
    )
    
    background_tasks.add_task(_resume_graph_background, thread_id)
    return {"status": "success"}

@router.get("/interview/{thread_id}", response_model=InterviewDeckDTO)
async def get_interview_data(thread_id: str):
    values, _, _ = _extract_state(thread_id)
    
    status = _get_run_status(thread_id)
    raw_qs = values.get("interview_questions", [])
    questions = []
    
    for idx, item in enumerate(raw_qs):
        if isinstance(item, str):
            questions.append(InterviewQuestionDTO(category=f"Q{idx+1}", question=item, answer=""))
        else:
            questions.append(InterviewQuestionDTO(
                category=item.get("category", f"Q{idx+1}"),
                question=item.get("question", str(item)),
                answer=item.get("answer") or item.get("suggested_answer") or ""
            ))
            
    if status == WorkflowStatus.COMPLETED or len(questions) > 0:
        deck_status = WorkflowStatus.READY.value
    else:
        deck_status = status.value
            
    return InterviewDeckDTO(thread_id=thread_id, status=deck_status, questions=questions)

@router.get("/outreach/{thread_id}", response_model=OutreachWorkspaceDTO)
async def get_outreach_data(thread_id: str):
    values, _, _ = _extract_state(thread_id)
    
    def _parse(items, default_type):
        out = []
        for it in items:
            if isinstance(it, str):
                out.append(OutreachCardDTO(type=default_type, subject="", body=it))
            else:
                out.append(OutreachCardDTO(
                    type=it.get("type", default_type),
                    subject=it.get("subject", ""),
                    body=it.get("body", str(it))
                ))
        return out

    cold_emails = _parse(values.get("cold_emails", []), "Cold Email")
    referrals = _parse(values.get("referral_templates", []), "Referral Request")
    followups = _parse(values.get("followup_templates", []), "Follow-Up")
    
    status = _get_run_status(thread_id)
    total = len(cold_emails) + len(referrals) + len(followups)
    
    if status == WorkflowStatus.COMPLETED or total > 0:
        ow_status = WorkflowStatus.READY.value
    else:
        ow_status = status.value
        
    return OutreachWorkspaceDTO(
        thread_id=thread_id,
        status=ow_status,
        cold_emails=cold_emails,
        referrals=referrals,
        followups=followups
    )

@router.get("/exports/{thread_id}")
async def get_exports_data(thread_id: str):
    values, _, _ = _extract_state(thread_id)
    
    resume_ready = values.get("optimized_resume") is not None
    interview_ready = len(values.get("interview_questions", [])) > 0
    outreach_ready = len(values.get("cold_emails", [])) > 0
    
    return {
        "resume_pdf": WorkflowStatus.READY.value if resume_ready else WorkflowStatus.PROCESSING.value,
        "interview_pdf": WorkflowStatus.READY.value if interview_ready else WorkflowStatus.PROCESSING.value,
        "outreach_zip": WorkflowStatus.READY.value if outreach_ready else WorkflowStatus.PROCESSING.value,
    }