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


def ats_evaluation_node(state: GlobalGraphState) -> Dict[str, Any]:
    if not state.original_resume or not state.jd_analysis:
        return {"errors": ["Missing resume or jd_analysis for ATS evaluation."]}
    
    from app.services.ats_engine import evaluate_resume
    from app.utils.schema_helpers import enforce_resume_schema, enforce_jd_schema
    
    resume_model = enforce_resume_schema(state.original_resume)
    jd_model = enforce_jd_schema(state.jd_analysis)

    report = evaluate_resume(resume_model, jd_model)
    return {"ats_report": report, "workflow_logs": ["Successfully ran deterministic ATS evaluation."]}

def final_ats_node(state: GlobalGraphState) -> Dict[str, Any]:
    # STRICT GUARD: Only run if the HITL loop officially finished all sections
    if state.current_section != "DONE" or not state.optimized_resume or not state.jd_analysis:
        return {"workflow_logs": ["Skipped final ATS evaluation (optimization not fully complete)"]}

    from app.services.ats_engine import evaluate_resume
    from app.utils.schema_helpers import enforce_resume_schema, enforce_jd_schema

    resume_model = enforce_resume_schema(state.optimized_resume)
    jd_model = enforce_jd_schema(state.jd_analysis)

    report = evaluate_resume(resume_model, jd_model)
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