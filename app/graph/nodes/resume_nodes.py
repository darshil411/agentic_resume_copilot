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
    OBJECTIVE

    Produce the strongest possible Projects section for THIS specific Job Description.

    The output should maximize:

    • ATS score
    • Technical credibility
    • Engineering depth
    • Recruiter impact

    PROCESS

    1. Compare every project available.

    2. Rank projects by relevance to the Job Description.

    3. Select the best projects.

    4. Rewrite them using the richest available technical evidence.

    5. Remove weaker or redundant projects if necessary.

    WHAT TO EMPHASIZE

    • System design

    • Architecture

    • Backend engineering

    • APIs

    • AI workflows

    • RAG

    • LangGraph

    • Performance

    • Scalability

    • Automation

    • Engineering ownership

    • Technical challenges solved

    • Quantifiable impact

    WHEN AVAILABLE

    Mention naturally

    • Languages

    • Frameworks

    • Libraries

    • Databases

    • Cloud

    • AI Models

    • Vector Databases

    • DevOps

    • Infrastructure

    • Testing

    • Security

    STYLE

    Every bullet should answer

    What was built?

    How was it built?

    Why was it valuable?

    Prefer strong engineering verbs.

    Architected

    Designed

    Engineered

    Implemented

    Developed

    Optimized

    Integrated

    Automated

    STRICT RULES

    Never invent information.

    Never invent metrics.

    Never invent technologies.

    Never invent architecture.

    Never invent responsibilities.

    Do not keyword stuff.

    Only use evidence from:

    1. Resume

    2. Project Knowledge Base

    OUTPUT

    Return ONLY the final Projects section in clean resume-ready markdown.
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

    project_context_block = f"""
    ====================================================
    PROJECT KNOWLEDGE BASE
    ====================================================

    You now have TWO independent sources of project information.

    SOURCE A
    ---------
    The Projects section already present in the resume.

    SOURCE B
    ---------
    A structured Project Knowledge Base generated from uploaded project documentation.

    The uploaded documentation belongs to the SAME candidate.

    It usually contains significantly richer technical details than the resume.

    ====================================================

    YOUR TASK

    Before generating the final Projects section:

    1. Read BOTH sources.

    2. Match projects that represent the same work.

    3. Use the Project Knowledge Base to enrich existing resume projects.

    4. Compare every project against the Job Description.

    5. Select ONLY the strongest and most relevant projects.

    6. You MAY reorder projects.

    7. You MAY replace weaker projects with stronger uploaded projects if they are more relevant.

    Your objective is NOT to preserve the original ordering.

    Your objective is to maximize ATS score while remaining completely truthful.

    ====================================================

    STRICT RULES

    Never invent projects.

    Never invent technologies.

    Never invent architecture.

    Never invent achievements.

    Never invent metrics.

    Never merge unrelated projects.

    Never use information that is not present in either source.

    ====================================================

    PROJECT KNOWLEDGE BASE

    {state.selected_project_context}

    ====================================================
    """

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
    {project_context_block}
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

def _apply_projects_proposal(new_content: str, original_projects: Any) -> Any:
    """Merge an LLM-generated Markdown projects section back onto the original
    Project objects, preserving metadata (title, tech_stack, urls).

    Strategy:
    1. Parse the Markdown for project headings (### Title) and the bullet
       lines that follow each heading.
    2. For each parsed heading, find the best-matching original Project by
       title (case-insensitive substring match).  If a match is found,
       update only its `description` (and optionally tech_stack from
       backtick-fenced tech hints) while keeping all other metadata intact.
    3. Any original project that was NOT mentioned in the optimized output
       is KEPT as-is (the optimizer may legitimately reduce the list, but
       we prefer not to silently drop projects whose heading the LLM merely
       reformatted).
    4. If the Markdown cannot be parsed at all, return the original list
       unchanged so we never corrupt the state.

    Returns a list of Project model instances.
    """
    from app.models.resume import Project
    import re

    # Normalise original_projects to a list of Project instances
    if not original_projects:
        return []

    orig_list: list = []
    for p in original_projects:
        if isinstance(p, dict):
            try:
                orig_list.append(Project(**p))
            except Exception:
                pass
        elif isinstance(p, Project):
            orig_list.append(p)

    if not orig_list:
        return original_projects  # nothing to merge into

    # ── Parse the Markdown ──────────────────────────────────────────────
    # Accept headings: ### Title, ## Title, **Title**, or "Title:"
    heading_re = re.compile(
        r'^(?:#{1,4}\s+|\*\*|)(.+?)(?:\*\*|:)?\s*$'
    )
    sections: list[tuple[str, list[str]]] = []  # [(heading_text, [bullet_lines])]
    current_heading: str | None = None
    current_bullets: list[str] = []

    for raw_line in new_content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        is_heading = (
            line.startswith('#')
            or (line.startswith('**') and line.endswith('**') and len(line) > 4)
        )
        if is_heading:
            if current_heading is not None:
                sections.append((current_heading, current_bullets))
            m = heading_re.match(line.lstrip('#').strip().strip('*'))
            current_heading = m.group(1).strip() if m else line.lstrip('#').strip().strip('*')
            current_bullets = []
        else:
            if current_heading is not None:
                current_bullets.append(line)

    if current_heading is not None:
        sections.append((current_heading, current_bullets))

    if not sections:
        # Unstructured output — return originals unchanged
        return orig_list

    # ── Match and update ────────────────────────────────────────────────
    updated_titles: set[str] = set()
    result_map: dict[str, Project] = {p.title: p for p in orig_list}

    for heading, bullets in sections:
        heading_lower = heading.lower()
        # Find the best original project match by title substring
        best_match: Project | None = None
        for proj in orig_list:
            if proj.title.lower() in heading_lower or heading_lower in proj.title.lower():
                best_match = proj
                break

        description = "\n".join(
            b.lstrip('-•* ').strip() for b in bullets if b.strip()
        ).strip()

        if best_match:
            # Update only description; preserve all other metadata
            updated = best_match.model_copy(
                update={"description": description or best_match.description}
            )
            result_map[best_match.title] = updated
            updated_titles.add(best_match.title)
        # If no match, this is a new project from the optimizer — add it
        # only if it has a meaningful description so we don't add blank entries
        elif description:
            new_proj = Project(title=heading, description=description)
            result_map[heading] = new_proj

    return list(result_map.values())


def _apply_education_proposal(new_content: str, original_education: Any) -> Any:
    """Merge an LLM-generated education section back onto the original
    Education objects, preserving college, degree, year and cgpa.

    The optimizer is allowed to add relevant coursework to the description
    field (we store it in `degree` suffix or ignore it — see strategy below).
    We NEVER overwrite college, degree, year or cgpa with fabricated content.

    Strategy:
    - If only one education entry exists and the proposal mentions it,
      keep the original object unchanged (the only safe action when the
      prompt returns a plain formatted string).
    - The optimizer prompt is factual-only, so returning the original
      unchanged is always safe for education.

    Returns a list of Education model instances.
    """
    from app.models.resume import Education

    if not original_education:
        return []

    edu_list: list = []
    for e in original_education:
        if isinstance(e, dict):
            try:
                edu_list.append(Education(**e))
            except Exception:
                pass
        elif isinstance(e, Education):
            edu_list.append(e)

    # Education is factual — return the validated originals unchanged.
    # The optimizer may have re-ordered or reformatted, but we have no
    # reliable way to merge free-form text back to structured fields without
    # risk of data loss.  Keeping originals is always correct.
    return edu_list if edu_list else original_education


def _parse_skills_string(skills_text: str, original_skills: Any) -> Any:
    """Parse a skills string (produced by the LLM skills optimizer) back into
    a StructuredSkills object so the ATS engine's schema contract is preserved.

    Expected input format (from the skills prompt):
        "Languages: Python, Go\nFrameworks: FastAPI, Django\n..."

    Any category label that doesn't match a known StructuredSkills field is
    placed into 'concepts'.  Skills already present in original_skills but
    absent from the parsed string are intentionally dropped — the optimizer
    may legitimately remove weak skills.

    Falls back to the original StructuredSkills if parsing yields nothing
    recognizable, to avoid silently discarding all skills.
    """
    from app.models.resume import StructuredSkills

    KNOWN_CATEGORIES = {
        # label (lowercased) → StructuredSkills field name
        "languages": "languages",
        "language": "languages",
        "frameworks": "frameworks",
        "framework": "frameworks",
        "libraries": "frameworks",
        "library": "frameworks",
        "ai/ml": "concepts",
        "ai": "concepts",
        "ml": "concepts",
        "tools": "tools",
        "tool": "tools",
        "devops": "tools",
        "cloud": "tools",
        "databases": "databases",
        "database": "databases",
        "db": "databases",
        "concepts": "concepts",
        "concept": "concepts",
        "other": "concepts",
    }

    result: Dict[str, list] = {
        "languages": [], "frameworks": [], "tools": [], "databases": [], "concepts": []
    }
    parsed_any = False

    for line in skills_text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Expect "Label: skill1, skill2, ..."
        if ":" in line:
            label, _, rest = line.partition(":")
            label_key = label.strip().lower()
            field = KNOWN_CATEGORIES.get(label_key, "concepts")
            skills = [s.strip() for s in rest.split(",") if s.strip()]
            result[field].extend(skills)
            if skills:
                parsed_any = True

    if not parsed_any:
        # LLM returned unstructured text — return the original skills unchanged
        return original_skills

    return StructuredSkills(
        languages=result["languages"],
        frameworks=result["frameworks"],
        tools=result["tools"],
        databases=result["databases"],
        concepts=result["concepts"],
    )


def commit_changes_node(state: GlobalGraphState) -> Dict[str, Any]:
    proposed = state.proposed_changes or {}
    section = state.current_section or "summary"
    
    optimized = copy.deepcopy(state.optimized_resume) if state.optimized_resume else copy.deepcopy(state.original_resume)
    
    new_content = proposed.get("new_content")
    status = (state.approval_state or {}).get(section, "")

    if status == "approved" and new_content and isinstance(new_content, str) and not new_content.startswith("⚠️"):
        if section == "skills":
            # Parse the skills string back into a StructuredSkills model
            if isinstance(optimized, dict):
                original_skills = optimized.get("skills")
                parsed_skills_model = _parse_skills_string(new_content, original_skills)
                optimized["skills"] = parsed_skills_model.model_dump() if hasattr(parsed_skills_model, "model_dump") else parsed_skills_model
            else:
                original_skills = getattr(optimized, "skills", None)
                optimized.skills = _parse_skills_string(new_content, original_skills)

        elif section == "projects":
            # Merge optimized Markdown back onto structured Project objects
            if isinstance(optimized, dict):
                original_projects = optimized.get("projects", [])
                merged = _apply_projects_proposal(new_content, original_projects)
                optimized["projects"] = [p.model_dump() if hasattr(p, "model_dump") else p for p in merged]
            else:
                original_projects = getattr(optimized, "projects", [])
                optimized.projects = _apply_projects_proposal(new_content, original_projects)

        elif section == "education":
            # Preserve structured Education objects; apply safe factual merge
            if isinstance(optimized, dict):
                original_education = optimized.get("education", [])
                merged = _apply_education_proposal(new_content, original_education)
                optimized["education"] = [e.model_dump() if hasattr(e, "model_dump") else e for e in merged]
            else:
                original_education = getattr(optimized, "education", [])
                optimized.education = _apply_education_proposal(new_content, original_education)

        else:
            # summary, experience, certifications — plain string fields
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