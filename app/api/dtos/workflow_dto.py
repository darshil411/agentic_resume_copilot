from pydantic import BaseModel
from typing import TypedDict
from datetime import datetime
from app.api.dtos.enums import WorkflowStatus

class BranchStatuses(TypedDict):
    resume_branch: WorkflowStatus
    interview_branch: WorkflowStatus
    outreach_branch: WorkflowStatus

class WorkflowMetadataDTO(BaseModel):
    thread_id: str
    created_at: datetime
    overall_status: WorkflowStatus
    active_branches: BranchStatuses
    current_review_section: str | None
    completed_sections: list[str]
