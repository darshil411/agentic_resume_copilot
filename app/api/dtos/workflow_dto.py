from pydantic import BaseModel # pyright: ignore[reportMissingImports]
from datetime import datetime
from typing import Any, Optional, List
from .enums import WorkflowStatus

class BranchStatuses(BaseModel):
    resume_branch: WorkflowStatus
    interview_branch: WorkflowStatus
    outreach_branch: WorkflowStatus

class WorkflowMetadataDTO(BaseModel):
    thread_id: str
    created_at: datetime
    overall_status: WorkflowStatus
    active_branches: BranchStatuses
    current_review_section: Optional[str]
    completed_sections: List[str]
    ats_report: Optional[Any] = None            # <-- ADD THIS LINE
    optimized_ats_report: Optional[Any] = None
    workflow_logs: List[str] = []