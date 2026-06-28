# app/graph/state.py (V2)
import operator
from pydantic import BaseModel, Field
from typing import Dict, Optional, List, Annotated
from ..schemas.resume import StructuredResume
from ..schemas.jd import JDAnalysis
from ..schemas.ats import ATSReport

class GraphState(BaseModel):
    # Core Inputs (File paths only to prevent checkpoint bloat)
    resume_file_path: Optional[str] = None
    job_description_text: Optional[str] = None
    
    # Processed Data
    resume_text: Optional[str] = None
    original_resume: Optional[StructuredResume] = None
    optimized_resume: Optional[StructuredResume] = None
    jd_analysis: Optional[JDAnalysis] = None
    ats_report: Optional[ATSReport] = None
    
    # Subgraph/Routing State
    current_section: Optional[str] = None
    proposed_changes: Dict = {}
    approval_state: Dict[str, str] = {}
    
    # Reducers: Annotated[Type, operator.add] tells LangGraph to APPEND, not overwrite.
    # This is critical for parallel execution and tracking workflow progress.
    section_retry_counts: Annotated[Dict[str, int], operator.add] = Field(default_factory=dict)
    workflow_logs: Annotated[List[str], operator.add] = Field(default_factory=list)
    errors: Annotated[List[str], operator.add] = Field(default_factory=list)
    human_feedback: Annotated[Dict[str, str], operator.add] = Field(default_factory=dict)