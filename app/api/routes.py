import os
import shutil
import uuid
import json
from typing import Optional, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from app.graph.builders.main_graph import build_main_graph
from app.utils.sqlite_checkpoint import get_checkpointer
from app.workers.background_jobs import init_bg_slot, get_interview_result, get_outreach_result

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
_task_versions: dict[str, dict[str, int]] = {}


# ---------------------------------------------------------------------------
# Status helpers
# ---------------------------------------------------------------------------

def _get_run_status(thread_id: str) -> WorkflowStatus:
    status = _run_status.get(thread_id, "running")

    if status.startswith("error"):
        return WorkflowStatus.FAILED

    if status == "done":
        return WorkflowStatus.COMPLETED

    if status == "action_required":
        return WorkflowStatus.ACTION_REQUIRED

    return WorkflowStatus.PROCESSING
# ---------------------------------------------------------------------------
# Graph runner helpers
# ---------------------------------------------------------------------------

def _run_graph_background(thread_id: str, initial_state: dict) -> None:
    config = {"configurable": {"thread_id": thread_id}}
    try:
        _run_status[thread_id] = "running"
        app_graph.invoke(initial_state, config=config)
        # Check whether the graph actually finished or paused on an interrupt
        state = app_graph.get_state(config)
        interrupt_detected = any(
        "__interrupt__" in str(task)
            for task in state.tasks
        )

        if interrupt_detected:
            _run_status[thread_id] = "action_required"
        elif state.next:
            _run_status[thread_id] = "running"
        else:
            _run_status[thread_id] = "done"
    except Exception as exc:
        _run_status[thread_id] = f"error: {exc}"


def _resume_graph_background(thread_id: str) -> None:
    config = {"configurable": {"thread_id": thread_id}}
    try:
        _run_status[thread_id] = "running"
        app_graph.invoke(None, config=config)
        # Check state again — another section may be ready for review
        state = app_graph.get_state(config)
        interrupt_detected = any(
            "__interrupt__" in str(task)
            for task in state.tasks
        )

        if interrupt_detected:
            _run_status[thread_id] = "action_required"
        elif state.next:
            _run_status[thread_id] = "running"
        else:
            _run_status[thread_id] = "done"
    except Exception as exc:
        _run_status[thread_id] = f"error: {exc}"


# ---------------------------------------------------------------------------
# State extraction
# ---------------------------------------------------------------------------

def _safe_to_dict(obj) -> dict:
    """Safely convert a Pydantic model or plain dict to a plain dict."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    try:
        return dict(obj)
    except Exception:
        return {}


def _extract_state(thread_id: str):
    """
    Returns (values_dict, all_next_nodes, target_config).
    Safely handles empty state, Pydantic vs dict subgraph tasks, and
    pulls resume-specific fields from the nested HITL subgraph task.
    """
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state_snapshot = app_graph.get_state(config)
    except Exception:
        return {}, [], config

    # Top-level state values
    values = _safe_to_dict(state_snapshot.values)
    all_next_nodes = list(state_snapshot.next) if state_snapshot.next else []
    target_config = config

    # Inspect subgraph tasks — HITL interrupt state lives here
    if hasattr(state_snapshot, "tasks") and state_snapshot.tasks:
        for task in state_snapshot.tasks:
            task_state = getattr(task, "state", None)
            if not task_state:
                continue

            # Collect next nodes from the subgraph
            if hasattr(task_state, "next") and task_state.next:
                all_next_nodes.extend(list(task_state.next))
                if hasattr(task_state, "config") and task_state.config:
                    target_config = task_state.config

            # Extract values — handles both Pydantic models and dicts
            task_values_raw = getattr(task_state, "values", task_state)
            task_values = _safe_to_dict(task_values_raw)

            # Prefer subgraph values for resume-specific fields
            for field in ("proposed_changes", "current_section", "approval_state", "human_feedback"):
                if task_values.get(field):
                    values[field] = task_values[field]

    return values, all_next_nodes, target_config


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

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
    init_bg_slot(thread_id)

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

    def _parse_branch(b_name: str) -> WorkflowStatus:
        s = branch_status_dict.get(b_name)
        if isinstance(s, WorkflowStatus):
            return s
        if s:
            try:
                return WorkflowStatus(s)
            except ValueError:
                return WorkflowStatus.PROCESSING
        return overall_status if overall_status != WorkflowStatus.ACTION_REQUIRED else WorkflowStatus.PROCESSING

    r_branch = _parse_branch("resume_branch")
    if "approval_processing_node" in all_next_nodes:
        r_branch = WorkflowStatus.ACTION_REQUIRED
        
    interview_slot = get_interview_result(thread_id)
    interview_status = WorkflowStatus(interview_slot.get("status", "PROCESSING"))
    
    outreach_slot = get_outreach_result(thread_id)
    outreach_status = WorkflowStatus(outreach_slot.get("status", "PROCESSING"))

    branches = BranchStatuses(
        resume_branch=r_branch,
        interview_branch=interview_status,
        outreach_branch=outreach_status
    )

    return WorkflowMetadataDTO(
        thread_id=thread_id,
        created_at=_workflow_creation_times.get(thread_id, datetime.now()),
        overall_status=overall_status,
        active_branches=branches,
        current_review_section=values.get("current_section"),
        completed_sections=[]
    )


@router.get("/resume/task/current/{thread_id}", response_model=ReviewTaskDTO)
async def get_current_resume_task(thread_id: str):
    try:
        values, all_next_nodes, _ = _extract_state(thread_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to extract graph state: {exc}")

    section = values.get("current_section") or "summary"
    overall_status = _get_run_status(thread_id)
    is_paused = _run_status.get(thread_id) == "action_required"
    status = WorkflowStatus.ACTION_REQUIRED if is_paused else overall_status

    if thread_id not in _task_versions:
        _task_versions[thread_id] = {}
    if section not in _task_versions[thread_id]:
        _task_versions[thread_id][section] = 1

    # proposed_changes may be a dict, Pydantic model, or None
    raw_proposal = _safe_to_dict(values.get("proposed_changes") or {})
    proposal_text = raw_proposal.get("new_content", "")
    reasoning_text = raw_proposal.get("reasoning", "")

    # original_resume: extract only the current section's text
    raw_original = _safe_to_dict(values.get("original_resume") or {})
    section_original = raw_original.get(section, "")
    if not isinstance(section_original, str):
        try:
            section_original = json.dumps(section_original, indent=2)
        except Exception:
            section_original = str(section_original)

    return ReviewTaskDTO(
        task_id=f"task_{thread_id}_{section}",
        version=_task_versions[thread_id][section],
        task_type="resume_section_review",
        section=section,
        status=status,
        created_at=datetime.now(),
        proposal=proposal_text,
        original=section_original,
        optimization_notes=reasoning_text,
        proposal_history=[]
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

    new_approval_state = dict(values.get("approval_state") or {})
    new_approval_state[section] = "approved"

    new_feedback_state = dict(values.get("human_feedback") or {})
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

    new_approval_state = dict(values.get("approval_state") or {})
    new_approval_state[section] = "rejected"

    new_feedback_state = dict(values.get("human_feedback") or {})
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
    slot = get_interview_result(thread_id)
    status = slot.get("status", WorkflowStatus.PROCESSING.value)
    data = slot.get("data") or {}
    
    raw_qs = data.get("interview_questions") or []
    questions = []

    for idx, item in enumerate(raw_qs):
        if isinstance(item, str):
            questions.append(InterviewQuestionDTO(category=f"Q{idx+1}", question=item, answer=""))
        elif isinstance(item, dict):
            questions.append(InterviewQuestionDTO(
                category=item.get("category", f"Q{idx+1}"),
                question=item.get("question", str(item)),
                answer=item.get("answer") or item.get("suggested_answer") or ""
            ))

    return InterviewDeckDTO(thread_id=thread_id, status=status, questions=questions)


@router.get("/outreach/{thread_id}", response_model=OutreachWorkspaceDTO)
async def get_outreach_data(thread_id: str):
    slot = get_outreach_result(thread_id)
    status = slot.get("status", WorkflowStatus.PROCESSING.value)
    data = slot.get("data") or {}

    def _parse(items, default_type):
        out = []
        for it in (items or []):
            if isinstance(it, str):
                out.append(OutreachCardDTO(type=default_type, subject="", body=it))
            elif isinstance(it, dict):
                out.append(OutreachCardDTO(
                    type=it.get("type", default_type),
                    subject=it.get("subject", ""),
                    body=it.get("body", str(it))
                ))
        return out

    cold_emails = _parse(data.get("cold_emails"), "Cold Email")
    referrals = _parse(data.get("referral_templates"), "Referral Request")
    followups = _parse(data.get("followup_templates"), "Follow-Up")

    return OutreachWorkspaceDTO(
        thread_id=thread_id,
        status=status,
        cold_emails=cold_emails,
        referrals=referrals,
        followups=followups
    )


@router.get("/exports/{thread_id}")
async def get_exports_data(thread_id: str):
    values, _, _ = _extract_state(thread_id)

    resume_ready = values.get("optimized_resume") is not None
    
    interview_slot = get_interview_result(thread_id)
    interview_ready = interview_slot.get("status") == "COMPLETED"
    
    outreach_slot = get_outreach_result(thread_id)
    outreach_ready = outreach_slot.get("status") == "COMPLETED"

    return {
        "resume_pdf": WorkflowStatus.READY.value if resume_ready else WorkflowStatus.PROCESSING.value,
        "interview_pdf": WorkflowStatus.READY.value if interview_ready else WorkflowStatus.PROCESSING.value,
        "outreach_zip": WorkflowStatus.READY.value if outreach_ready else WorkflowStatus.PROCESSING.value,
    }

@router.get("/exports/{thread_id}/resume")
async def download_resume(thread_id: str):
    values, _, _ = _extract_state(thread_id)
    optimized = values.get("optimized_resume")
    if not optimized:
        raise HTTPException(status_code=404, detail="Optimized resume not ready yet.")
        
    # Render basic plain text
    content = []
    if isinstance(optimized, dict):
        for section, text in optimized.items():
            if section not in ("name", "email", "phone", "city", "linkedin", "github", "portfolio", "certifications"):
                content.append(f"--- {section.upper()} ---")
                if isinstance(text, list):
                    content.append("\n".join(str(i) for i in text))
                else:
                    content.append(str(text))
                content.append("\n")
    else:
        content.append(str(optimized))
        
    return PlainTextResponse(
        "\n".join(content),
        headers={"Content-Disposition": "attachment; filename=optimized_resume.txt"}
    )

@router.get("/exports/{thread_id}/interview")
async def download_interview(thread_id: str):
    slot = get_interview_result(thread_id)
    if slot.get("status") != "COMPLETED":
        raise HTTPException(status_code=404, detail="Interview deck not ready yet.")
        
    data = slot.get("data") or {}
    questions = data.get("interview_questions") or []
    
    content = ["--- INTERVIEW STRATEGY DECK ---\n"]
    for q in questions:
        if isinstance(q, dict):
            content.append(f"Q: {q.get('question', '')}")
            content.append(f"A: {q.get('answer', q.get('suggested_answer', ''))}\n")
        else:
            content.append(str(q))
            
    return PlainTextResponse(
        "\n".join(content),
        headers={"Content-Disposition": "attachment; filename=interview_prep.txt"}
    )

@router.get("/exports/{thread_id}/outreach")
async def download_outreach(thread_id: str):
    slot = get_outreach_result(thread_id)
    if slot.get("status") != "COMPLETED":
        raise HTTPException(status_code=404, detail="Outreach toolkit not ready yet.")
        
    data = slot.get("data") or {}
    
    content = ["--- OUTREACH TOOLKIT ---\n"]
    
    content.append("COLD EMAILS:")
    for email in data.get("cold_emails", []):
        content.append(str(email))
        content.append("\n")
        
    content.append("REFERRAL REQUESTS:")
    for ref in data.get("referral_templates", []):
        content.append(str(ref))
        content.append("\n")
        
    content.append("FOLLOW-UPS:")
    for f in data.get("followup_templates", []):
        content.append(str(f))
        content.append("\n")
            
    return PlainTextResponse(
        "\n".join(content),
        headers={"Content-Disposition": "attachment; filename=outreach_toolkit.txt"}
    )
