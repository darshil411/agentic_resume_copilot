from pydantic import BaseModel
from datetime import datetime
from typing import Any
from app.api.dtos.enums import WorkflowStatus

class ReviewTaskDTO(BaseModel):
    task_id: str
    version: int
    task_type: str
    section: str
    status: WorkflowStatus
    created_at: datetime
    proposal: dict[str, Any] | str
    original: dict[str, Any] | str
    optimization_notes: str
    proposal_history: list["ReviewTaskDTO"] = []
