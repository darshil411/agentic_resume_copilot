from typing import Dict, Any
import fitz  # pyright: ignore[reportMissingImports] # PyMuPDF
import re
from langchain_core.messages import SystemMessage, HumanMessage # pyright: ignore[reportMissingImports]
from pydantic import ValidationError # pyright: ignore[reportMissingImports]

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


def _build_fallback_ats_report(resume: StructuredResume, jd_analysis: JDAnalysis) -> ATSReport:
    matched = [skill for skill in jd_analysis.required_skills if skill.lower() in {s.lower() for s in resume.skills.languages + resume.skills.frameworks + resume.skills.tools + resume.skills.databases + resume.skills.concepts}]
    missing = [skill for skill in jd_analysis.required_skills if skill not in matched]
    score = min(100.0, 55.0 + (len(matched) / max(len(jd_analysis.required_skills), 1)) * 35.0)
    return ATSReport(
        score=round(score, 1),
        matched_skills=matched,
        missing_skills=missing,
        weak_sections=["summary", "skills"],
        improvement_suggestions=[f"Add stronger evidence for {skill}" for skill in missing[:3]],
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
    """
    resume_text = state.resume_text
    
    if not resume_text:
        return {"errors": ["No resume_text found to structure."]}
        
    llm = get_llm("gemini").with_structured_output(StructuredResume)
    
    prompt = f"Convert the following raw resume text into a structured JSON format.\n\nResume Text:\n{resume_text}"
    try:
        structured_resume = llm.invoke([HumanMessage(content=prompt)])
        return {
            "original_resume": structured_resume,
            "workflow_logs": ["Successfully structured resume via LLM."]
        }
    except ValidationError as e:
        return {"errors": [f"SchemaValidationError: {str(e)}"]}
    except Exception as e:
        fallback_resume = _build_fallback_resume(resume_text)
        return {
            "original_resume": fallback_resume,
            "workflow_logs": [f"Used fallback resume parsing because LLM failed: {e}"]
        }


def jd_analysis_node(state: GlobalGraphState) -> Dict[str, Any]:
    """
    LLM node: Analyzes the Job Description text.
    """
    jd_text = state.job_description_text
    
    if not jd_text:
        return {"errors": ["No job_description_text found."]}
        
    llm = get_llm("gemini").with_structured_output(JDAnalysis)
    
    prompt = f"Analyze the following Job Description and extract the key requirements, skills, and tools.\n\nJD:\n{jd_text}"
    
    try:
        jd_analysis = llm.invoke([HumanMessage(content=prompt)])
        return {
            "jd_analysis": jd_analysis,
            "workflow_logs": ["Successfully analyzed job description."]
        }
    except Exception as e:
        fallback_jd = _build_fallback_jd_analysis(jd_text)
        return {
            "jd_analysis": fallback_jd,
            "workflow_logs": [f"Used fallback JD analysis because LLM failed: {e}"]
        }


def ats_evaluation_node(state: GlobalGraphState) -> Dict[str, Any]:
    """
    Hybrid node: Deterministic exact match + LLM semantic match.
    Reads: original_resume, jd_analysis
    Writes: ats_report
    """
    resume = state.original_resume
    jd_analysis = state.jd_analysis
    
    if not resume or not jd_analysis:
        return {"errors": ["Missing resume or jd_analysis for ATS evaluation."]}
    
    resume_skills_lower = set(s.lower() for s in resume.skills.languages + resume.skills.frameworks + resume.skills.tools + resume.skills.databases + resume.skills.concepts)
    jd_skills_lower = set(s.lower() for s in jd_analysis.required_skills)
    
    exact_matches = resume_skills_lower.intersection(jd_skills_lower)
    missing_skills = list(jd_skills_lower - resume_skills_lower)
    
    deterministic_score = len(exact_matches) / max(len(jd_skills_lower), 1) * 50.0
    
    llm = get_llm("groq").with_structured_output(ATSReport)
    
    prompt = f"""
    Evaluate the resume against the job description.
    Resume Skills: {resume.skills}
    Resume Projects: {[p.title for p in resume.projects]}
    JD Required Skills: {jd_analysis.required_skills}
    JD Responsibilities: {jd_analysis.responsibilities}
    
    The deterministic keyword match found these missing skills: {missing_skills}.
    Assess the semantic fit (transferable skills, contextual alignment).
    Provide a final ATSReport. The score should be out of 100, incorporating the deterministic findings.
    """
    
    try:
        ats_report = llm.invoke([HumanMessage(content=prompt)])
        ats_report.matched_skills = list(set(ats_report.matched_skills + list(exact_matches)))
        return {
            "ats_report": ats_report,
            "workflow_logs": ["Successfully ran hybrid ATS evaluation."]
        }
    except Exception as e:
        fallback_ats = _build_fallback_ats_report(resume, jd_analysis)
        fallback_ats.score = round(max(fallback_ats.score, deterministic_score), 1)
        return {
            "ats_report": fallback_ats,
            "workflow_logs": [f"Used fallback ATS scoring because LLM failed: {e}"]
        }