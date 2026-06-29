from typing import TypedDict, Annotated, Optional, List, Dict, Any
from app.models.resume import StructuredResume
from app.models.jd import JDAnalysis
from app.models.ats import ATSReport
from app.graph.state.reducers import append_list, merge_dicts

class GlobalGraphState(TypedDict):
    """
    Global shared orchestration state for the entire graph.
    Uses TypedDict for LangGraph compatibility but stores strongly typed Pydantic models.
    All subgraph output fields MUST be declared here so LangGraph can write them back
    into the parent graph's checkpoint after a subgraph finishes.
    """
    # Raw Inputs
    resume_file_path: str
    resume_text: str
    job_description_text: str
    
    # Core Data Models
    original_resume: Optional[StructuredResume]
    optimized_resume: Optional[StructuredResume]
    jd_analysis: Optional[JDAnalysis]
    ats_report: Optional[ATSReport]
    
    # Resume Subgraph local fields (needed for HITL pass-through)
    current_section: Optional[str]
    proposed_changes: Optional[Dict[str, Any]]
    approval_state: Optional[Dict[str, Any]]
    section_retry_counts: Dict[str, int]
    resume_export_paths: Dict[str, str]

    # Interview Subgraph outputs — must live in global state for fan-in to work
    interview_questions: List[str]
    interview_experiences: List[str]
    prep_roadmap: List[str]

    # Outreach Subgraph outputs — must live in global state for fan-in to work
    cold_emails: List[str]
    referral_templates: List[str]
    followup_templates: List[str]

    # Execution Tracking with Reducers for merge-safe parallel updates
    workflow_logs: Annotated[List[str], append_list]
    errors: Annotated[List[str], append_list]
    branch_status: Annotated[Dict[str, str], merge_dicts]
