import os
import shutil
import uuid
import json
import threading
from typing import Optional, List, Dict, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from langgraph.types import Command

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
_thread_locks: dict[str, threading.Lock] = {}

def _get_lock(thread_id: str) -> threading.Lock:
    if thread_id not in _thread_locks:
        _thread_locks[thread_id] = threading.Lock()
    return _thread_locks[thread_id]

def _get_run_status(thread_id: str) -> WorkflowStatus:
    status = _run_status.get(thread_id, "running")
    if status.startswith("error"):
        return WorkflowStatus.FAILED
    if status == "done":
        return WorkflowStatus.COMPLETED
    if status == "action_required":
        return WorkflowStatus.ACTION_REQUIRED
    return WorkflowStatus.PROCESSING

def _safe_to_dict(obj) -> dict:
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

def _format_content_for_ui(content: Any) -> str:
    """FIX: Robust serializer to ensure Lists/Dicts render correctly in React textareas."""
    if not content:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        formatted = []
        for item in content:
            if isinstance(item, dict):
                formatted.append(json.dumps(item, indent=2))
            else:
                formatted.append(str(item))
        return "\n\n".join(formatted)
    if isinstance(content, dict):
        return json.dumps(content, indent=2)
    return str(content)

def _extract_state(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state_snapshot = app_graph.get_state(config)
    except Exception:
        return {}, False, {}

    values = _safe_to_dict(getattr(state_snapshot, "values", {}))
    is_interrupted = False
    interrupt_payload = {}

    if getattr(state_snapshot, "tasks", None):
        for task in state_snapshot.tasks:
            if getattr(task, "interrupts", ()):
                is_interrupted = True
                if len(task.interrupts) > 0 and hasattr(task.interrupts[0], "value"):
                    interrupt_payload = task.interrupts[0].value
            
            task_state = getattr(task, "state", None)
            if task_state and getattr(task_state, "tasks", None):
                for subtask in task_state.tasks:
                    if getattr(subtask, "interrupts", ()):
                        is_interrupted = True
                        if len(subtask.interrupts) > 0 and hasattr(subtask.interrupts[0], "value"):
                            interrupt_payload = subtask.interrupts[0].value

    return values, is_interrupted, interrupt_payload

def _advance_graph(thread_id: str, command=None, initial_state=None) -> None:
    lock = _get_lock(thread_id)
    if not lock.acquire(blocking=False):
        return

    try:
        _run_status[thread_id] = "running"
        config = {"configurable": {"thread_id": thread_id}}
        payload = command if command is not None else initial_state
        
        app_graph.invoke(payload, config=config)

        _, is_interrupted, _ = _extract_state(thread_id)
        state_snapshot = app_graph.get_state(config)

        if is_interrupted:
            _run_status[thread_id] = "action_required"
        elif getattr(state_snapshot, "next", None):
            _run_status[thread_id] = "running"
        else:
            _run_status[thread_id] = "done"
    except Exception as exc:
        _run_status[thread_id] = f"error: {exc}"
    finally:
        lock.release()

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

    background_tasks.add_task(_advance_graph, thread_id, None, initial_state)
    return {"thread_id": thread_id, "status": "RUNNING"}

@router.get("/workflow/{thread_id}", response_model=WorkflowMetadataDTO)
async def get_workflow_metadata(thread_id: str):
    values, is_interrupted, _ = _extract_state(thread_id)
    overall_status = WorkflowStatus.ACTION_REQUIRED if is_interrupted else _get_run_status(thread_id)
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

    r_branch = WorkflowStatus.ACTION_REQUIRED if is_interrupted else _parse_branch("resume_branch")
    interview_slot = get_interview_result(thread_id)
    outreach_slot = get_outreach_result(thread_id)

    branches = BranchStatuses(
        resume_branch=r_branch,
        interview_branch=WorkflowStatus(interview_slot.get("status", "PROCESSING")),
        outreach_branch=WorkflowStatus(outreach_slot.get("status", "PROCESSING"))
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
        values, is_interrupted, interrupt_payload = _extract_state(thread_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to extract graph state: {exc}")

    overall_status = _get_run_status(thread_id)
    status = WorkflowStatus.ACTION_REQUIRED if is_interrupted else overall_status

    if is_interrupted and interrupt_payload and interrupt_payload.get("type") == "resume_review":
        section = interrupt_payload.get("section", "summary")
        raw_proposal = interrupt_payload.get("proposal", {})
    else:
        section = values.get("current_section") or "summary"
        raw_proposal = _safe_to_dict(values.get("proposed_changes") or {})

    if thread_id not in _task_versions:
        _task_versions[thread_id] = {}
    if section not in _task_versions[thread_id]:
        _task_versions[thread_id][section] = 1

    # FIX: Robust serialization so UI never receives broken objects
    proposal_text = _format_content_for_ui(raw_proposal.get("new_content", ""))
    reasoning_text = raw_proposal.get("reasoning", "")

    raw_original = _safe_to_dict(values.get("original_resume") or {})
    section_original = _format_content_for_ui(raw_original.get(section, ""))

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
    values, is_interrupted, interrupt_payload = _extract_state(thread_id)
    
    if not is_interrupted:
        return {"status": "ignored", "detail": "Task is already processing"}

    background_tasks.add_task(_advance_graph, thread_id, Command(resume={"action": "approve", "feedback": request.feedback}))
    return {"status": "success"}

@router.post("/resume/task/regenerate/{thread_id}")
async def regenerate_resume_task(thread_id: str, request: TaskApprovalRequest, background_tasks: BackgroundTasks):
    values, is_interrupted, interrupt_payload = _extract_state(thread_id)

    if not is_interrupted:
        return {"status": "ignored", "detail": "Task is already processing"}

    section = interrupt_payload.get("section", "summary") if interrupt_payload else "summary"
    _task_versions[thread_id][section] = _task_versions.get(thread_id, {}).get(section, 1) + 1

    background_tasks.add_task(_advance_graph, thread_id, Command(resume={"action": "reject", "feedback": request.feedback}))
    return {"status": "success"}

@router.post("/resume/task/skip/{thread_id}")
async def skip_resume_task(thread_id: str, request: TaskApprovalRequest, background_tasks: BackgroundTasks):
    values, is_interrupted, _ = _extract_state(thread_id)

    if not is_interrupted:
        return {"status": "ignored", "detail": "Task is already processing"}

    background_tasks.add_task(_advance_graph, thread_id, Command(resume={"action": "skip", "feedback": ""}))
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

@router.get("/exports/{thread_id}/resume")
async def download_resume(thread_id: str):
    values, _, _ = _extract_state(thread_id)
    optimized = values.get("optimized_resume")
    if not optimized:
        raise HTTPException(status_code=404, detail="Optimized resume not ready yet.")
        
    content = []
    if isinstance(optimized, dict):
        name = optimized.get("name", "")
        if name:
            content.append(name)
        contact_parts = [v for k, v in optimized.items() if k in ("email", "phone", "city", "linkedin") and v]
        if contact_parts:
            content.append(" | ".join(contact_parts))
        content.append("")
        
        for section in ("summary", "skills", "experience", "projects", "education", "certifications"):
            text = optimized.get(section)
            if not text:
                continue
            content.append(f"--- {section.upper()} ---")
            if isinstance(text, list):
                for item in text:
                    content.append(str(item))
            elif isinstance(text, dict):
                for k, v in text.items():
                    content.append(f"{k}: {', '.join(v) if isinstance(v, list) else v}")
            else:
                content.append(str(text))
            content.append("")
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
    
    content = ["--- INTERVIEW STRATEGY DECK ---", ""]
    for idx, q in enumerate(questions):
        if isinstance(q, dict):
            content.append(f"Q{idx+1}: {q.get('question', '')}")
            ans = q.get('answer') or q.get('suggested_answer', '')
            if ans:
                content.append(f"A: {ans}")
            content.append("")
        else:
            content.append(f"Q{idx+1}: {q}")
            content.append("")
            
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
    
    content = ["--- OUTREACH TOOLKIT ---", ""]
    
    for idx, email in enumerate(data.get("cold_emails", [])):
        content.append(f"COLD EMAIL {idx+1}:")
        content.append(str(email))
        content.append("")
        
    for idx, ref in enumerate(data.get("referral_templates", [])):
        content.append(f"REFERRAL REQUEST {idx+1}:")
        content.append(str(ref))
        content.append("")
        
    for idx, f in enumerate(data.get("followup_templates", [])):
        content.append(f"FOLLOW-UP {idx+1}:")
        content.append(str(f))
        content.append("")
            
    return PlainTextResponse(
        "\n".join(content),
        headers={"Content-Disposition": "attachment; filename=outreach_toolkit.txt"}
    )

@router.get("/exports/{thread_id}")
async def get_exports_data(thread_id: str):
    values, _, _ = _extract_state(thread_id)

    resume_ready = values.get("optimized_resume") is not None
    interview_slot = get_interview_result(thread_id)
    outreach_slot = get_outreach_result(thread_id)

    return {
        "resume_pdf": WorkflowStatus.READY.value if resume_ready else WorkflowStatus.PROCESSING.value,
        "interview_pdf": WorkflowStatus.READY.value if interview_slot.get("status") == "COMPLETED" else WorkflowStatus.PROCESSING.value,
        "outreach_zip": WorkflowStatus.READY.value if outreach_slot.get("status") == "COMPLETED" else WorkflowStatus.PROCESSING.value,
    }

@router.get("/original-resume/{thread_id}")
async def get_original_resume(thread_id: str):
    values, _, _ = _extract_state(thread_id)
    original = values.get("original_resume")
    if not original:
        raise HTTPException(status_code=404, detail="Original resume not yet extracted.")
    if isinstance(original, dict):
        return original
    return _safe_to_dict(original)