from typing import Dict, Any
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field
import copy
from langgraph.types import interrupt
from app.graph.state.global_state import GlobalGraphState
from app.utils.llm_factory import get_llm

class ProposedChanges(BaseModel):
    new_content: str = Field(description="The proposed optimized text for the section")
    reasoning: str = Field(description="Why this change improves the ATS score or impact")

def _get_section_data(original_resume: Any, section: str) -> Any:
    if not original_resume:
        return None
    if isinstance(original_resume, dict):
        return original_resume.get(section)
    return getattr(original_resume, section, None)

def _is_section_empty(value: Any) -> bool:
    """Recursive deep check to catch empty lists, empty dicts, and string nulls."""
    if value is None:
        return True
    if isinstance(value, list):
        return all(_is_section_empty(item) for item in value)
    if isinstance(value, dict):
        return all(_is_section_empty(v) for v in value.values())
        
    text = str(value).strip().lower()
    if not text or text in ("none", "null", "n/a", "not provided", "missing", "empty", "[]", "{}"):
        return True
    return False

SECTION_PROMPTS = {
    "summary": """
    OBJECTIVE:
    Rewrite the professional summary into a concise, technically strong, recruiter-friendly introduction.

    RULES:
    - Keep it between 3–5 lines.
    - Focus on technical strengths, specialization, and engineering capability.
    - Mention strongest technologies naturally.
    - Align with the target role and ATS keywords.
    - Sound confident and professional, NOT exaggerated.
    - DO NOT use buzzword-heavy fluff like:
      "hardworking", "team player", "passionate learner".
    - DO NOT invent fake years of experience.
    - DO NOT use first-person language ("I", "my").

    GOOD SUMMARY STYLE:
    "AI-focused software engineer skilled in LangGraph, FastAPI, and LLM orchestration, with experience building structured agentic workflows, ATS optimization systems, and scalable backend pipelines."

    OUTPUT:
    Clean professional paragraph only.
    """,

    "skills": """
    OBJECTIVE:
    Reorganize and optimize the skills section for ATS readability and recruiter scanning.

    RULES:
    - Group skills into logical categories.
    - Example categories:
      Languages, Frameworks, AI/ML, Databases, Tools, Cloud.
    - Prioritize skills relevant to the job description.
    - Remove redundant or weak technologies.
    - DO NOT invent technologies.
    - DO NOT add skills unsupported by projects or experience.
    - Keep formatting extremely clean and scannable.

    OUTPUT FORMAT:
    Category: Skill1, Skill2, Skill3
    """,

    "projects": """
    OBJECTIVE:
    Rewrite project descriptions to emphasize engineering complexity, architecture, ownership, and technical impact.

    RULES:
    - Use strong engineering action verbs.
    - Focus on:
      architecture,
      backend systems,
      scalability,
      orchestration,
      APIs,
      performance,
      automation,
      AI workflows.
    - Explain WHAT was built,
      HOW it was built,
      WHY it mattered.
    - Quantify impact ONLY if clearly supported by the original content.
    - If metrics are unavailable, improve technical depth WITHOUT inventing fake numbers.
    - Mention technologies naturally within bullets.
    - Avoid generic resume filler language.

    BULLET STYLE:
    - Architected...
    - Developed...
    - Engineered...
    - Implemented...
    - Optimized...

    STRICT RULES:
    - NO hallucinated companies/users/revenue.
    - NO fake scaling claims.
    - NO fake production metrics.

    OUTPUT:
    Clean markdown bullet points only.
    """,

    "experience": """
    OBJECTIVE:
    Rewrite work experience to emphasize ownership, technical contribution, system design, and measurable engineering value.

    RULES:
    - Use concise, high-impact bullet points.
    - Focus on:
      backend systems,
      APIs,
      optimization,
      automation,
      scalability,
      AI integration,
      architecture decisions.
    - Use the XYZ style naturally:
      Accomplished X by implementing Y resulting in Z.
    - Add metrics ONLY if strongly implied or already present.
    - Avoid fake business metrics.
    - Avoid generic phrases like:
      "Worked on",
      "Responsible for",
      "Helped with".

    PRIORITY:
    Ownership > Participation.

    GOOD BULLET STYLE:
    "Engineered a FastAPI-based orchestration backend integrating LangGraph workflows and structured state management for AI resume optimization."

    OUTPUT:
    Resume-ready markdown bullet points only.
    """,

    "education": """
    OBJECTIVE:
    Keep education concise, factual, and ATS-friendly.

    RULES:
    - Preserve factual accuracy.
    - Include:
      degree,
      university,
      graduation year,
      CGPA if available.
    - Optionally add:
      relevant coursework
      ONLY if relevant to the target role.
    - DO NOT generate fake achievements.
    - DO NOT generate fake research/work.
    - Keep formatting clean.

    OUTPUT:
    Clean factual education section only.
    """,

    "certifications": """
    OBJECTIVE:
    Format certifications clearly for recruiter readability and ATS parsing.

    RULES:
    - Preserve exact certification names.
    - Mention issuer/platform if available.
    - Keep formatting simple and professional.
    - Prioritize certifications relevant to the JD.
    - DO NOT hallucinate certification providers or dates.

    OUTPUT:
    Clean certification list only.
    """
}

def optimize_section_node(state: GlobalGraphState) -> Dict[str, Any]:
    section = state.current_section or "summary"
    original = state.original_resume
    ats_report = state.ats_report
    
    feedback_dict = state.human_feedback or {}
    feedback_text = feedback_dict.get(section, "")
    
    raw_section = _get_section_data(original, section)

    # SMART SKIP: Bypass the LLM call entirely if the section has no real data
    if _is_section_empty(raw_section):
        return {
            "workflow_logs": [f"Skipped optimization for missing/empty section: {section}"],
            "approval_state": {section: "skipped"},
            "proposed_changes": {"new_content": "null", "reasoning": "Section was empty."}
        }

    current_text = "\n".join([str(x) for x in raw_section]) if isinstance(raw_section, list) else str(raw_section).strip()

    feedback_block = (
        f"\n\nIMPORTANT: The human reviewer rejected the previous draft with this feedback:\n"
        f"\"{feedback_text}\"\n"
        f"You MUST incorporate this feedback directly in the new version."
        if feedback_text else ""
    )

    section_rules = SECTION_PROMPTS.get(
        section.lower(),
        """
        Optimize this resume section for ATS compatibility,
        recruiter readability,
        and technical clarity while preserving factual accuracy.
        """
    )

    prompt = f"""
    You are a senior technical resume strategist specializing in software engineering, AI systems, backend engineering, and agentic AI workflows.

    Your job is to improve ONE specific resume section while preserving factual accuracy.

    TARGET SECTION:
    {section.upper()}

    JOB DESCRIPTION ATS REQUIREMENTS:
    {ats_report.missing_skills if ats_report else []}

    ORIGINAL SECTION CONTENT:
    -------------------------
    {current_text}
    -------------------------

    {feedback_block}

    SECTION-SPECIFIC OPTIMIZATION INSTRUCTIONS:
    {section_rules}

    GLOBAL RULES:
    - Preserve factual accuracy.
    - Improve recruiter readability.
    - Improve ATS alignment naturally.
    - Avoid keyword stuffing.
    - Avoid fake metrics.
    - Avoid exaggerated claims.
    - Preserve original technical meaning.
    - Keep formatting clean and resume-ready.
    - Output ONLY final resume content.
    - DO NOT include explanations or chat responses.
    """

    try:
        llm = get_llm("cerebras").with_structured_output(ProposedChanges)
        # 1. Added config tags to trace Cerebras usage and token burn
        proposed = llm.invoke(
            [HumanMessage(content=prompt)],
            config={"tags": ["provider:cerebras", f"section:{section}"]}
        )
        
        # STRICT NULL-GUARD: Reject empty LLM responses
        if not proposed or not proposed.new_content or proposed.new_content.strip() == "":
            raise ValueError("LLM returned empty proposal")
            
        return {
            "proposed_changes": proposed.model_dump(),
            "workflow_logs": [f"Generated proposal for '{section}'"]
        }
    except Exception as cerebras_error:
        try:
            llm = get_llm("gemini").with_structured_output(ProposedChanges)
            # 2. Added config tags to track Fallback activations specifically
            proposed = llm.invoke(
                [HumanMessage(content=prompt)],
                config={"tags": ["provider:gemini", "fallback_triggered", f"section:{section}"]}
            )
            
            if not proposed or not proposed.new_content or proposed.new_content.strip() == "":
                raise ValueError("LLM returned empty proposal")
                
            return {
                "proposed_changes": proposed.model_dump(),
                "workflow_logs": [f"Generated proposal for '{section}'"]
            }
        except Exception as e:
            return {
                "errors": [f"optimize_section_node failed: {str(e)}"],
                "proposed_changes": {
                    "new_content": f"⚠️ [AI Error] Failed to optimize '{section}'. Please click 'Try Again'.",
                    "reasoning": "Providers failed or returned empty content. Check API keys and rate limits."
                }
            }

def approval_processing_node(state: GlobalGraphState) -> Dict[str, Any]:
    section = state.current_section or "summary"
    
    approval_state = state.approval_state or {}
    if approval_state.get(section) == "skipped":
        return {"workflow_logs": [f"Auto-skipped empty section: {section}"]}

    # EXACT HITL PAYLOAD: LangGraph freezes here and embeds this dict into the interrupt object
    decision = interrupt({
        "type": "resume_review",
        "section": section,
        "proposal": state.proposed_changes or {},
    })

    action = (decision or {}).get("action")
    feedback = (decision or {}).get("feedback", "")

    if action == "skip":
        return {"approval_state": {section: "skipped"}, "workflow_logs": [f"User skipped: {section}"]}

    if action == "approve":
        return {
            "approval_state": {section: "approved"},
            "human_feedback": {section: feedback},
            "workflow_logs": [f"Approved: {section}"]
        }

    counts_dict = state.section_retry_counts or {}
    current_count = counts_dict.get(section, 0)
    return {
        "approval_state": {section: "rejected"},
        "human_feedback": {section: feedback},
        "section_retry_counts": {section: current_count + 1},
        "workflow_logs": [f"Regenerating: {section} - Attempt {current_count + 1}"]
    }

def commit_changes_node(state: GlobalGraphState) -> Dict[str, Any]:
    proposed = state.proposed_changes or {}
    section = state.current_section or "summary"
    
    optimized = copy.deepcopy(state.optimized_resume) if state.optimized_resume else copy.deepcopy(state.original_resume)
    
    new_content = proposed.get("new_content")
    status = (state.approval_state or {}).get(section, "")

    if status == "approved" and new_content and isinstance(new_content, str) and not new_content.startswith("⚠️"):
        if isinstance(optimized, dict):
            optimized[section] = new_content
        else:
            setattr(optimized, section, new_content)
        
    master_sequence = ["summary", "skills", "experience", "projects", "education", "certifications"]
    
    try:
        current_idx = master_sequence.index(section)
    except ValueError:
        current_idx = -1
        
    next_section = "DONE"
    
    # SMART FAST-FORWARD: Scan ahead and only pause on sections with actual data
    for i in range(current_idx + 1, len(master_sequence)):
        candidate = master_sequence[i]
        candidate_data = _get_section_data(state.original_resume, candidate)
        if not _is_section_empty(candidate_data):
            next_section = candidate
            break
        
    return {
        "optimized_resume": optimized,
        "current_section": next_section,
        "proposed_changes": {}, 
        "workflow_logs": [f"Committed changes for '{section}', advancing to '{next_section}'"]
    }