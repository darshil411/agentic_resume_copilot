from typing import Annotated, Optional, List, Dict, Any
from pydantic import BaseModel, Field

from app.graph.state.reducers import append_list, merge_dicts
from app.models.resume import StructuredResume
from app.models.jd import JDAnalysis
from app.models.ats import ATSReport

class GlobalGraphState(BaseModel):
    # Core Inputs
    resume_file_path: Optional[str] = None
    job_description_text: Optional[str] = None
    
    # Foundation Nodes Output
    resume_text: Optional[str] = None
    original_resume: Optional[StructuredResume] = None
    jd_analysis: Optional[JDAnalysis] = None
    ats_report: Optional[ATSReport] = None
    optimized_resume: Optional[StructuredResume] = None
    
    # Resume Subgraph
    current_section: Optional[str] = None
    proposed_changes: Optional[Dict[str, Any]] = None
    approval_state: Optional[Dict[str, Any]] = None
    human_feedback: Optional[Dict[str, str]] = None
    section_retry_counts: Optional[Dict[str, int]] = None
    resume_export_paths: Optional[Dict[str, str]] = None
    
    # Interview Subgraph
    company_research: Optional[Dict[str, Any]] = None
    interview_questions: Optional[List[Any]] = None
    interview_experiences: Optional[List[Any]] = None
    prep_roadmap: Optional[List[Any]] = None
    interview_export_paths: Optional[Dict[str, str]] = None
    
    # Outreach Subgraph
    cold_emails: Optional[List[Any]] = None
    referral_templates: Optional[List[Any]] = None
    followup_templates: Optional[List[Any]] = None
    outreach_export_paths: Optional[Dict[str, str]] = None
    
    # Global channels
    workflow_logs: Annotated[List[str], append_list] = Field(default_factory=list)
    errors: Annotated[List[str], append_list] = Field(default_factory=list)
    branch_status: Annotated[Dict[str, str], merge_dicts] = Field(default_factory=dict)
