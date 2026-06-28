from typing import TypedDict, Optional, List, Dict, Any

class ResumeSubgraphState(TypedDict):
    """
    Local state for the Resume Optimization HITL Subgraph.
    This state is only relevant to the resume optimization pipeline.
    """
    current_section: Optional[str]
    proposed_changes: Optional[Dict[str, Any]]
    approval_state: Optional[Dict[str, Any]]  # Stores HITL approval input (e.g., {"approved": True, "feedback": "..."})
    section_retry_counts: Dict[str, int]
    resume_export_paths: Dict[str, str]

class InterviewSubgraphState(TypedDict):
    """
    Local state for the Interview Preparation Subgraph.
    """
    company_research: Optional[Dict[str, Any]]
    interview_questions: List[str]
    interview_experiences: List[str]
    prep_roadmap: List[str]
    interview_export_paths: Dict[str, str]

class OutreachSubgraphState(TypedDict):
    """
    Local state for the Outreach Generation Subgraph.
    """
    cold_emails: List[str]
    referral_templates: List[str]
    followup_templates: List[str]
    outreach_export_paths: Dict[str, str]
