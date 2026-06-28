from pydantic import BaseModel # pyright: ignore[reportMissingImports]
from typing import Dict, Optional

from ..schemas.resume import StructuredResume
from ..schemas.jd import JDAnalysis
from ..schemas.ats import ATSReport


class GraphState(BaseModel):

    resume_file_path: Optional[str] = None

    resume_text: Optional[str] = None

    job_description_text: Optional[str] = None

    original_resume: Optional[StructuredResume] = None

    optimized_resume: Optional[StructuredResume] = None

    jd_analysis: Optional[JDAnalysis] = None

    ats_report: Optional[ATSReport] = None

    current_section: Optional[str] = None

    approval_status: Dict[str, str] = {}

    retry_counts: Dict[str, int] = {}

    proposed_changes: Dict = {}

    human_feedback: Dict[str, str] = {}

    final_resume_path: Optional[str] = None