from typing import Dict, Any, List
from langchain_core.messages import HumanMessage # pyright: ignore[reportMissingImports]
from pydantic import BaseModel, Field # pyright: ignore[reportMissingImports]

# Imported GlobalGraphState to ensure strict type synchronization across subgraphs
from app.graph.state.global_state import GlobalGraphState
from app.utils.llm_factory import get_llm

class OutreachOutput(BaseModel):
    cold_emails: List[str] = Field(description="Cold email templates for recruiters or hiring managers")
    referrals: List[str] = Field(description="Messages asking for referrals")
    followups: List[str] = Field(description="Follow-up emails after an application or interview")

def generate_outreach_templates_node(state: GlobalGraphState) -> Dict[str, Any]:
    """
    LLM Node: Generates outreach templates.
    Operates completely independently on the original resume and JD.
    """
    # FIX: Switched from state.get() to standard Pydantic dot-notation to avoid AttributeError crashes
    resume = state.original_resume
    jd_analysis = state.jd_analysis
    
    if not resume or not jd_analysis:
        return {"errors": ["Missing original_resume or jd_analysis for outreach."]}
        
    # Uses centralized factory default for Groq ("openai/gpt-oss-120b" or equivalent modern 2026 model)
    llm = get_llm("groq").with_structured_output(OutreachOutput)
    
    prompt = f"""
    Create professional outreach templates (cold email, referral request, follow-up) 
    based on the candidate's original resume summary and the target job description.
    
    Summary: {resume.summary}
    Target Role Info: {jd_analysis.keywords}
    """
    
    try:
        output = llm.invoke([HumanMessage(content=prompt)])
        return {
            "cold_emails": output.cold_emails,
            "referral_templates": output.referrals,
            "followup_templates": output.followups,
            "branch_status": {"outreach_pipeline": "COMPLETED"},
            "workflow_logs": ["Generated outreach templates."]
        }
    except Exception as e:
        return {"errors": [f"generate_outreach_node failed: {str(e)}"]}