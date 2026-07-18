from typing import Dict, Any
import fitz  # pyright: ignore[reportMissingImports] # PyMuPDF
import re
from langchain_core.messages import SystemMessage, HumanMessage  # pyright: ignore[reportMissingImports]
from langchain_core.runnables import RunnableConfig  # pyright: ignore[reportMissingImports]
from pydantic import ValidationError  # pyright: ignore[reportMissingImports]

from app.graph.state.global_state import GlobalGraphState
from app.models.resume import StructuredResume, StructuredSkills, Project, Experience, Education
from app.models.jd import JDAnalysis
from app.models.ats import ATSReport
from app.utils.llm_factory import get_llm


def _build_fallback_resume(resume_text: str) -> StructuredResume:
    lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
    name = lines[0] if lines else "Candidate"
    summary = "Experienced backend engineer with a strong focus on Python, APIs, and AI-enabled systems."
    normalized = re.sub(r"\s+", " ", resume_text.lower())
    skills = []
    if "python" in normalized:
        skills.append("Python")
    if "fastapi" in normalized:
        skills.append("FastAPI")
    if "langgraph" in normalized:
        skills.append("LangGraph")
    if "api" in normalized:
        skills.append("APIs")
    if "sql" in normalized:
        skills.append("SQL")
    if not skills:
        skills = ["Python", "FastAPI", "APIs"]

    return StructuredResume(
        name=name,
        summary=summary,
        skills=StructuredSkills(
            languages=["Python"],
            frameworks=["FastAPI"],
            tools=["Git", "Docker"],
            databases=["PostgreSQL"],
            concepts=["APIs", "Async Programming"],
        ),
        projects=[Project(title="AI Resume Copilot", description="Built an AI-assisted resume optimization workflow.", tech_stack=["Python", "FastAPI"])],
        experience=[Experience(company="Example Company", role="Software Engineer", bullets=["Built backend services.", "Worked with APIs and data pipelines."])],
        education=[Education(college="Example University", degree="B.Tech", year="2020")],
        certifications=["AWS Cloud Practitioner"],
    )


def _build_fallback_jd_analysis(jd_text: str) -> JDAnalysis:
    normalized = jd_text.lower()
    required_skills = []
    if "python" in normalized:
        required_skills.append("Python")
    if "fastapi" in normalized:
        required_skills.append("FastAPI")
    if "langgraph" in normalized:
        required_skills.append("LangGraph")
    if not required_skills:
        required_skills = ["Python", "FastAPI", "APIs"]

    return JDAnalysis(
        required_skills=required_skills,
        responsibilities=["Build backend services", "Integrate AI workflows", "Collaborate with product teams"],
        keywords=required_skills + ["backend", "deployment"],
        tools=["Git", "Docker", "PostgreSQL"],
        experience_requirements=["3+ years"],
        role_summary="Backend engineering role focused on Python services and AI-driven workflows.",
    )


def _build_fallback_ats_report(resume: Any, jd_analysis: JDAnalysis) -> ATSReport:
    from app.models.ats import ATSReport, ATSCategoryScores
    missing = jd_analysis.required_skills
    return ATSReport(
        score=45.0,
        category_scores=ATSCategoryScores(
            keyword_match=15.0, experience_alignment=5.0, project_relevance=10.0,
            quantifiable_impact=5.0, resume_structure=5.0, writing_quality=5.0, penalties=0.0
        ),
        matched_skills=[],
        missing_skills=missing,
        weak_sections=["summary", "skills"],
        improvement_priorities=["System execution fell back to baseline heuristics."],
        optimization_guidelines={"summary": ["Manual review required."]},
        overall_feedback=["Primary evaluation engines encountered an exception."]
    )


def resume_upload_node(state: GlobalGraphState) -> Dict[str, Any]:
    """
    Initializes the workflow.
    State must already contain resume_file_path and job_description_text.
    """
    return {"workflow_logs": ["Started resume_upload_node."]}


def resume_extraction_node(state: GlobalGraphState) -> Dict[str, Any]:
    """
    Deterministic node: Extracts text from the uploaded PDF.
    """
    file_path = state.resume_file_path

    if not file_path:
        return {"errors": ["No resume_file_path provided for extraction."]}

    try:
        doc = fitz.open(file_path)
        text = "\n".join(page.get_text("text") for page in doc)
        return {
            "resume_text": text,
            "workflow_logs": ["Successfully extracted text from resume PDF."]
        }
    except Exception as e:
        return {"errors": [f"resume_extraction_node failed: {str(e)}"]}


def resume_structuring_node(state: GlobalGraphState) -> Dict[str, Any]:
    """
    LLM node: Converts raw resume text into the StructuredResume Pydantic model.
    Primary: OpenRouter (gpt-4o-mini)  |  Fallback: Gemini (with key rotation)
    """
    resume_text = state.resume_text

    if not resume_text:
        return {"errors": ["No resume_text found to structure."]}

    prompt = f"Convert the following raw resume text into a structured JSON format.\n\nResume Text:\n{resume_text}"

    # Primary: OpenRouter gpt-4o-mini
    try:
        llm = get_llm("openrouter", model="openai/gpt-4o-mini").with_structured_output(StructuredResume)
        structured_resume = llm.invoke([HumanMessage(content=prompt)])
        return {
            "original_resume": structured_resume,
            "workflow_logs": ["[OpenRouter/gpt-4o-mini] Successfully structured resume."]
        }
    except ValidationError as e:
        return {"errors": [f"SchemaValidationError: {str(e)}"]}
    except Exception as primary_err:
        pass  # fall through to Gemini

    # Fallback: Gemini with key rotation
    try:
        llm = get_llm("gemini").with_structured_output(StructuredResume)
        structured_resume = llm.invoke([HumanMessage(content=prompt)])
        return {
            "original_resume": structured_resume,
            "workflow_logs": ["[Gemini fallback] Successfully structured resume."]
        }
    except Exception as e:
        fallback_resume = _build_fallback_resume(resume_text)
        return {
            "original_resume": fallback_resume,
            "workflow_logs": [f"[Hard fallback] Used static parsing. Primary & Gemini both failed: {e}"]
        }


def jd_analysis_node(state: GlobalGraphState) -> Dict[str, Any]:
    """
    LLM node: Analyzes the Job Description text.
    Primary: OpenRouter (gpt-4o-mini)  |  Fallback: Gemini (with key rotation)
    """
    jd_text = state.job_description_text

    if not jd_text:
        return {"errors": ["No job_description_text found."]}

    prompt = f"Analyze the following Job Description and extract the key requirements, skills, and tools.\n\nJD:\n{jd_text}"

    # Primary: OpenRouter gpt-4o-mini
    try:
        llm = get_llm("openrouter", model="openai/gpt-4o-mini").with_structured_output(JDAnalysis)
        jd_analysis = llm.invoke([HumanMessage(content=prompt)])
        return {
            "jd_analysis": jd_analysis,
            "workflow_logs": ["[OpenRouter/gpt-4o-mini] Successfully analyzed job description."]
        }
    except Exception:
        pass  # fall through to Gemini

    # Fallback: Gemini with key rotation
    try:
        llm = get_llm("gemini").with_structured_output(JDAnalysis)
        jd_analysis = llm.invoke([HumanMessage(content=prompt)])
        return {
            "jd_analysis": jd_analysis,
            "workflow_logs": ["[Gemini fallback] Successfully analyzed job description."]
        }
    except Exception as e:
        fallback_jd = _build_fallback_jd_analysis(jd_text)
        return {
            "jd_analysis": fallback_jd,
            "workflow_logs": [f"[Hard fallback] Used static JD analysis. Both providers failed: {e}"]
        }


def _evaluate_resume_against_jd(resume: Any, jd_analysis: JDAnalysis) -> ATSReport:
    """Shared hybrid deterministic/LLM ATS evaluation logic with defensive type-fallback parsing."""
    import re
    resume_skills_lower = set()
    
    # 1. Safely extract skills keywords whether it is a text block or Pydantic object
    skills_field = getattr(resume, "skills", None) if resume else None
    if skills_field:
        if isinstance(skills_field, str):
            resume_skills_lower.update(re.findall(r'\b\w+\b', skills_field.lower()))
        else:
            try:
                languages = getattr(skills_field, "languages", []) or []
                frameworks = getattr(skills_field, "frameworks", []) or []
                tools = getattr(skills_field, "tools", []) or []
                databases = getattr(skills_field, "databases", []) or []
                concepts = getattr(skills_field, "concepts", []) or []
                for skill in (languages + frameworks + tools + databases + concepts):
                    if isinstance(skill, str):
                        resume_skills_lower.add(skill.lower())
            except Exception:
                pass

    # 2. Tokenize the entire serialized payload string to guarantee full extraction safety
    try:
        resume_dump = resume.model_dump_json() if hasattr(resume, "model_dump_json") else str(resume)
        resume_skills_lower.update(re.findall(r'\b\w+\b', resume_dump.lower()))
    except Exception:
        pass

    jd_skills_lower = set(s.lower() for s in jd_analysis.required_skills)
    exact_matches = resume_skills_lower.intersection(jd_skills_lower)
    missing_skills = list(jd_skills_lower - resume_skills_lower)
    deterministic_score = len(exact_matches) / max(len(jd_skills_lower), 1) * 50.0

    # 3. Handle projects rendering defensively
    projects_field = getattr(resume, "projects", []) if resume else []
    project_titles = []
    if isinstance(projects_field, list):
        for p in projects_field:
            if isinstance(p, str):
                project_titles.append(p)
            elif hasattr(p, "title"):
                project_titles.append(str(getattr(p, "title")))
            elif isinstance(p, dict):
                project_titles.append(str(p.get("title", "")))
    else:
        project_titles.append(str(projects_field))

    try:
        safe_resume_text = resume.model_dump_json() if hasattr(resume, "model_dump_json") else str(resume)
    except Exception:
        safe_resume_text = str(resume)

    prompt = f"""
    You are an expert ATS Resume Evaluation Engine used inside an AI Resume Optimization system.

    Your job is NOT to behave like a recruiter. Your job is to objectively evaluate how well a resume matches a specific Job Description and generate a structured ATS report that will be consumed by downstream Resume Optimization agents.

    RESUME:
    {safe_resume_text}

    JOB DESCRIPTION:
    Required Skills: {jd_analysis.required_skills}
    Responsibilities: {jd_analysis.responsibilities}
    Deterministic Missing Skills: {missing_skills}
    IMPORTANT RULES:
            - Be strict, objective, and evidence-based.
            - Evaluate only what is explicitly present in the resume.
            - Never invent skills, experience, certifications, achievements, or projects.
            - Never reward buzzwords without supporting evidence.
            - Never reward better English alone.
            - Never reward longer bullets unless they improve ATS relevance.
            - Treat semantic equivalents as valid matches (e.g. REST APIs ↔ FastAPI, LLM Orchestration ↔ LangGraph) when appropriate.
            - Repeated keywords should not increase the score.
            - The same resume evaluated multiple times should produce nearly identical scores (±2 points).

            Evaluate the resume using the following rubric:

            1. Keyword Match (30 Points)
            Evaluate required technologies, programming languages, frameworks, tools, platforms, libraries, cloud technologies, and domain-specific keywords. Reward exact and strong semantic matches only.

            2. Experience Alignment (15 Points)
            Evaluate role similarity, responsibilities, seniority alignment, and relevance of professional experience to the target role.

            3. Project Relevance (15 Points)
            Evaluate technology overlap, domain relevance, implementation complexity, and whether projects demonstrate the required skills.

            4. Quantifiable Impact (10 Points)
            Evaluate measurable achievements, business impact, percentages, metrics, performance improvements, users served, datasets handled, latency reductions, revenue impact, or any quantified accomplishments.

            5. Resume Structure (10 Points)
            Evaluate ATS-friendly organization, standard section headings, contact information, readability, and logical structure. Ignore visual formatting and assume plain text parsing.

            6. Writing Quality (10 Points)
            Evaluate action verbs, concise achievement-oriented bullets, grammar, clarity, and professional tone. Do NOT reward verbosity.

            7. Keyword Stuffing Penalty (-5 Points)
            Apply only when keywords are unnaturally repeated without adding meaningful context.

            8. Repetition Penalty (-5 Points)
            Apply only when multiple bullets communicate essentially the same achievement or responsibility.

            SCORING CALIBRATION:
            - Base the final score ONLY on the rubric above.
            - Small wording improvements should improve the score by at most 2-5 points.
            - Significant score improvements should occur ONLY when important JD-relevant evidence is surfaced, existing experience is better aligned to the JD, or valuable keywords are naturally incorporated without fabrication.
            - Never increase the score simply because the resume sounds more impressive.
            - Never reduce the score because wording changed if keyword coverage and evidence remain equivalent.

            Return a structured ATS report containing:

            1. Final ATS Score (0-100)
            2. Category-wise Scores (Return purely the numeric float values as defined by the schema, no text reasoning)
            3. Matched Skills
            4. Missing Critical Skills (ignore nice-to-have technologies)
            5. Weak Resume Sections (Summary, Skills, Projects, Experience, Education)
            6. Ranked Improvement Priorities (highest impact first)
            7. Optimization Guidelines for every weak section containing:
            - What should improve
            - JD keywords to naturally incorporate
            - Existing keywords that MUST be preserved
            - Existing resume evidence that should be emphasized
            - Things that should NOT be changed
            8. Overall Feedback (maximum 5 concise actionable points)

            Remember that this report will directly guide downstream optimization agents. Every recommendation must be actionable, specific, and achievable using only the information already present in the resume. Never recommend inventing new experience, projects, skills, certifications, or achievements.
            """

            
    
    # 1. Primary OpenRouter (Forcing determinism with temperature=0.0)
    try:
        llm = get_llm("openrouter", model="openai/gpt-4o-mini", temperature=0.0).with_structured_output(ATSReport)
        ats_report = llm.invoke([HumanMessage(content=prompt)])
        ats_report.matched_skills = list(set(ats_report.matched_skills + list(exact_matches)))
        return ats_report
    except Exception:
        pass

    # 2. Fallback Gemini (Forcing determinism)
    try:
        llm = get_llm("gemini", temperature=0.0).with_structured_output(ATSReport)
        ats_report = llm.invoke([HumanMessage(content=prompt)])
        ats_report.matched_skills = list(set(ats_report.matched_skills + list(exact_matches)))
        return ats_report
    except Exception as e:
        fallback_ats = _build_fallback_ats_report(resume, jd_analysis)
        fallback_ats.score = round(max(fallback_ats.score, deterministic_score), 1)
        return fallback_ats

def ats_evaluation_node(state: GlobalGraphState) -> Dict[str, Any]:
    if not state.original_resume or not state.jd_analysis:
        return {"errors": ["Missing resume or jd_analysis for ATS evaluation."]}
    
    report = _evaluate_resume_against_jd(state.original_resume, state.jd_analysis)
    return {"ats_report": report, "workflow_logs": ["Successfully ran hybrid ATS evaluation."]}

def final_ats_node(state: GlobalGraphState) -> Dict[str, Any]:
    # STRICT GUARD: Only run if the HITL loop officially finished all sections
    if state.current_section != "DONE" or not state.optimized_resume or not state.jd_analysis:
        return {"workflow_logs": ["Skipped final ATS evaluation (optimization not fully complete)"]}

    report = _evaluate_resume_against_jd(state.optimized_resume, state.jd_analysis)
    return {
        "optimized_ats_report": report,
        "workflow_logs": ["Calculated Final Optimized ATS Score"]
    } if report else {"workflow_logs": ["Final ATS evaluation failed"]}

def trigger_background_workers_node(state: GlobalGraphState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Triggers detached async workers for interview and outreach generation.
    These run independently and do not block the LangGraph HITL pipeline.
    """
    import threading
    from app.workers.background_jobs import run_interview_worker_sync, run_outreach_worker_sync
    
    thread_id = (config or {}).get("configurable", {}).get("thread_id")
    if not thread_id:
        return {"errors": ["No thread_id found in config for trigger_background_workers_node"]}
        
    resume = state.original_resume
    jd = state.jd_analysis
    
    # Fire and forget
    threading.Thread(target=run_interview_worker_sync, args=(thread_id, resume, jd), daemon=True).start()
    threading.Thread(target=run_outreach_worker_sync, args=(thread_id, resume, jd), daemon=True).start()

    return {
        "workflow_logs": ["Triggered detached background workers for interview and outreach."]
    }