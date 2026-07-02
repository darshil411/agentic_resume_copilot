from typing import Dict, Any, List
from langchain_core.messages import HumanMessage  # pyright: ignore[reportMissingImports]
from pydantic import BaseModel, Field  # pyright: ignore[reportMissingImports]

from app.graph.state.global_state import GlobalGraphState
from app.utils.llm_factory import get_llm


class OutreachOutput(BaseModel):
    cold_emails: List[str] = Field(description="Cold email templates for recruiters or hiring managers")
    referrals: List[str] = Field(description="Messages asking for referrals from connections")
    followups: List[str] = Field(description="Follow-up emails after an application or interview")


_FALLBACK_COLD_EMAIL = [
    "Hi [Name], I came across the [Role] opening at [Company] and I'm very excited about it. "
    "My background in Python, FastAPI, and AI systems aligns closely with your requirements. "
    "I'd love to connect and learn more about the team. Best, [Your Name]"
]
_FALLBACK_REFERRAL = [
    "Hi [Name], I hope you're doing well! I noticed [Company] is hiring for [Role] and I think "
    "it's a great fit for my background. Would you be open to referring me? I'd be happy to share "
    "my resume. Thanks so much!"
]
_FALLBACK_FOLLOWUP = [
    "Hi [Name], I wanted to follow up on my application for the [Role] position at [Company]. "
    "I remain very enthusiastic about the opportunity and would love to discuss how I can contribute. "
    "Please let me know if you need any additional information. Best, [Your Name]"
]


def generate_outreach_templates_node(state: GlobalGraphState) -> Dict[str, Any]:
    """
    LLM Node: Generates outreach templates (cold email, referral, follow-up).
    Primary: Groq (llama-3.1-8b-instant)  |  Fallback: Gemini (with key rotation)
    Operates on original_resume and jd_analysis — independent of optimization pipeline.
    """
    resume = state.original_resume
    jd_analysis = state.jd_analysis

    if not resume or not jd_analysis:
        return {"errors": ["Missing original_resume or jd_analysis for outreach."]}

    prompt = f"""
    Create professional, personalized outreach templates for a job applicant.
    Generate one cold email, one referral request message, and one follow-up email.
    Keep them concise, warm, and specific to the role.

    Candidate Summary: {resume.summary}
    Target Role Keywords: {jd_analysis.keywords}
    Required Skills: {jd_analysis.required_skills}
    """

    # Primary: Groq llama-3.1-8b-instant
    try:
        llm = get_llm("groq").with_structured_output(OutreachOutput)
        output = llm.invoke([HumanMessage(content=prompt)])
        return {
            "cold_emails": output.cold_emails,
            "referral_templates": output.referrals,
            "followup_templates": output.followups,
            "branch_status": {"outreach_pipeline": "COMPLETED"},
            "workflow_logs": ["[Groq/llama-3.1-8b] Generated outreach templates."]
        }
    except Exception:
        pass  # fall through to Gemini

    # Fallback: Gemini with key rotation
    try:
        llm = get_llm("gemini").with_structured_output(OutreachOutput)
        output = llm.invoke([HumanMessage(content=prompt)])
        return {
            "cold_emails": output.cold_emails,
            "referral_templates": output.referrals,
            "followup_templates": output.followups,
            "branch_status": {"outreach_pipeline": "COMPLETED"},
            "workflow_logs": ["[Gemini fallback] Generated outreach templates."]
        }
    except Exception as e:
        # Hard fallback: placeholder templates so branch doesn't crash
        return {
            "cold_emails": _FALLBACK_COLD_EMAIL,
            "referral_templates": _FALLBACK_REFERRAL,
            "followup_templates": _FALLBACK_FOLLOWUP,
            "branch_status": {"outreach_pipeline": "COMPLETED"},
            "workflow_logs": [f"[Hard fallback] Used generic outreach templates. Both providers failed: {e}"],
            "errors": [f"generate_outreach_templates_node: all providers failed: {str(e)}"]
        }