from typing import TypedDict, Annotated, Optional, List, Dict
from app.models.resume import StructuredResume
from app.models.jd import JDAnalysis
from app.models.ats import ATSReport
from app.graph.state.reducers import append_list, merge_dicts

class GlobalGraphState(TypedDict):
    """
    Global shared orchestration state for the entire graph.
    Uses TypedDict for LangGraph compatibility but stores strongly typed Pydantic models.
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
    
    # Execution Tracking with Reducers for merge-safe parallel updates
    workflow_logs: Annotated[List[str], append_list]
    errors: Annotated[List[str], append_list]
    branch_status: Annotated[Dict[str, str], merge_dicts]
