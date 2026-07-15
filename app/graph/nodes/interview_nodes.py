import os
import json
from typing import Dict, Any, List
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from app.graph.state.global_state import GlobalGraphState
from app.utils.llm_factory import get_llm

class InterviewQuestion(BaseModel):
    round_type: str = Field(description="Must be one of: Recruiter Screen, Technical/DSA, Project Deep Dive, Behavioral, Hiring Manager")
    question: str = Field(description="Realistic engineering discussion or scenario question. Avoid basic trivia.")
    interviewer_intent: str = Field(description="The hidden engineering or behavioral evaluation goal behind this question")
    strategy: str = Field(description="Step-by-step guidance on how the candidate should answer this using the X-Y-Z formula")
    project_to_highlight: str = Field(description="The exact name of the selected project from the candidate's background to use as proof")

class InterviewPrepOutput(BaseModel):
    company_intel: List[str] = Field(description="3-4 bullet points outlining tech landscape, tech stack, and verified news")
    experiences: List[str] = Field(description="3-4 items outlining the specific structure of the hiring loop")
    company_questions: List[str] = Field(description="3 real historic questions found from public internet records")
    roadmap: List[str] = Field(description="A 7-day targeted preparation timeline")
    confidence_score: str = Field(description="Must be HIGH, MEDIUM, or LOW based on grounding confidence")
    source_basis: List[str] = Field(description="Explicit context sources utilized (e.g., Glassdoor forum metrics, corporate tech blog docs)")
    questions: List[InterviewQuestion] = Field(description="EXACTLY 5 grounded interview questions matching the 5 required rounds")

class CompressionSchema(BaseModel):
    summary_points: List[str] = Field(description="Compressed, unique bullet points extracting vital trends")

def _filter_tavily_results(results: list) -> str:
    """Filters out low-quality, short, or duplicate snippets from Tavily."""
    seen = set()
    clean_snippets = []
    for r in results:
        content = r.get("content", "").strip()
        if len(content) < 120:
            continue
        normalized = content[:60].lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        clean_snippets.append(content)
    return "\n".join(clean_snippets)

def _select_relevant_projects(projects: Any, jd_keywords: List[str]) -> List[dict]:
    """Programmatically extracts the top 2 most relevant projects to save prompt token clutter."""
    if not projects:
        return []
    
    project_list = projects if isinstance(projects, list) else []
    if len(project_list) <= 2:
        return [dict(p) if hasattr(p, "dict") else p for p in project_list]
        
    scored_projects = []
    for p in project_list:
        p_dict = p.dict() if hasattr(p, "dict") else dict(p)
        text = f"{p_dict.get('title','')} {p_dict.get('description','')} {' '.join(p_dict.get('tech_stack',[]))}".lower()
        score = sum(1 for kw in jd_keywords if str(kw).lower() in text)
        scored_projects.append((score, p_dict))
        
    scored_projects.sort(key=lambda x: x[0], reverse=True)
    return [p[1] for p in scored_projects[:2]]

def _compress_context(raw_text: str, topic: str) -> List[str]:
    """Uses a fast LLM pass to compress noisy web results into structured summaries."""
    if not raw_text or raw_text.strip() == "":
        return [f"General industry standard context for {topic}"]
    try:
        prompt = f"Compress the following raw internet search text about '{topic}' into 4 unique, concise, high-signal bullet points:\n\n{raw_text}"
        llm = get_llm("groq").with_structured_output(CompressionSchema)
        res = llm.invoke([HumanMessage(content=prompt)])
        return res.summary_points
    except Exception:
        return [line.strip("- ") for line in raw_text.split("\n") if line.strip()][:3]

def generate_interview_prep_node(state: GlobalGraphState) -> Dict[str, Any]:
    resume = state.original_resume
    jd_analysis = state.jd_analysis

    if not resume or not jd_analysis:
        return {"errors": ["Missing core input context models."]}

    company = getattr(jd_analysis, "company_name", "Target Company") or "Target Company"
    role = getattr(jd_analysis, "role_summary", "Engineer")
    keywords = getattr(jd_analysis, "keywords", [])

    # Step 1: Programmatic Resume Extraction
    raw_projects = getattr(resume, "projects", [])
    selected_projects = _select_relevant_projects(raw_projects, keywords)
    relevant_skills = getattr(resume, "skills", {})

    # Step 2: High-Volume Tavily Retrieval (max_results=5)
    intel_text, loop_text = "", ""
    tavily_key = os.environ.get("TAVILY_API_KEY")
    if tavily_key:
        try:
            from tavily import TavilyClient
            t_client = TavilyClient(api_key=tavily_key)
            
            res1 = t_client.search(query=f"{company} engineering architecture tech stack updates 2026", max_results=5)
            intel_text = _filter_tavily_results(res1.get("results", []))
            
            res2 = t_client.search(query=f"{company} {role} interview loops questions process glassdoor reddit", max_results=5)
            loop_text = _filter_tavily_results(res2.get("results", []))
        except Exception as e:
            print(f"[Tavily Stage Error]: {e}")

    # Step 3: Context Compression Passes
    compressed_intel = _compress_context(intel_text, f"{company} Technical Architecture")
    compressed_patterns = _compress_context(loop_text, f"{company} Interview Loop Structures")

    # Step 4: Grounded Strategy Generation Prompt
    prompt = f"""
    You are a principal technical interviewer designing a highly realistic interview preparation strategy dossier.
    
    Target Context:
    - Firm Name: {company}
    - Targeted Role: {role}
    - Specific Job Duties: {jd_analysis.responsibilities}
    
    Grounded Candidate Background:
    - Selected Relevant Projects: {json.dumps(selected_projects, indent=2)}
    - Candidate Core Skills Stack: {relevant_skills}

    Verified Corporate Environment Summaries:
    {json.dumps(compressed_intel, indent=2)}

    Observed Corporate Interview Patterns:
    {json.dumps(compressed_patterns, indent=2)}

    STRICT GENERATION MANDATES:
    1. Generate EXACTLY 5 questions matching these 5 chronological blocks: Recruiter Screen, Technical/DSA, Project Deep Dive, Behavioral, Hiring Manager.
    2. NEVER invent corporate internal systems or architectures unless explicitly validated by the Verified Corporate Environment Summaries.
    3. Ground every single question strategy explicitly within the provided 'Selected Relevant Projects'. State the exact project title to highlight.
    4. Focus heavily on actual engineering design discussion rather than generic syntax trivia.
    """

    # SWAPPED: Run Gemini first as it handles complex nested JSON schemas much better than Groq
    for provider in ("gemini", "groq"):
        try:
            llm = get_llm(provider).with_structured_output(InterviewPrepOutput)
            output = llm.invoke([HumanMessage(content=prompt)], config={"tags": [f"provider:{provider}", "interview_strategy"]})
            
            processed_qs = []
            for q in output.questions:
                processed_qs.append({
                    # FIX: Removed the deprecated 'q.category' attribute. Now correctly maps 'round_type'
                    "category": q.round_type,
                    "question": q.question,
                    "interviewer_intent": q.interviewer_intent,
                    "strategy": q.strategy,
                    "project_to_highlight": q.project_to_highlight
                })

            return {
                "company_research": {
                    "company_intel": output.company_intel,
                    "interview_experiences": output.experiences,
                    "company_questions": output.company_questions,
                    "prep_roadmap": output.roadmap,
                    "confidence_score": output.confidence_score,
                    "source_basis": output.source_basis,
                    "tailored_questions": processed_qs
                },
                "branch_status": {"interview_pipeline": "COMPLETED"},
                "workflow_logs": [f"Successfully constructed grounded interview dossier using {provider} engine metrics."]
            }
        except Exception as err:
            print(f"[Engine Fault] Layer {provider} aborted generation: {err}")

    # Fallback structure state mapping
    return {
        "company_research": {
            "company_intel": ["Focus: Core systems engineering", "Architecture: Cloud native scaling standard layers"],
            "interview_experiences": ["Round 1: Screening Call", "Round 2: Technical Loop Panel"],
            "company_questions": ["Explain how you ensure transaction consistency across distributed environments."],
            "prep_roadmap": ["Day 1-4: Review systems maps", "Day 5-7: STAR behavioral mapping exercises"],
            "confidence_score": "LOW",
            "source_basis": ["Fallback automation data presets"],
            "tailored_questions": [{
                "category": "Project Deep Dive | Technical",
                "question": "Walk me through the load capacity limits of your engineering repository systems.",
                "interviewer_intent": "Evaluate structural validation and bottleneck awareness metrics.",
                "strategy": "Structure details around optimization bounds.",
                "project_to_highlight": "Primary Portfolio Project"
            }]
        },
        "branch_status": {"interview_pipeline": "COMPLETED"},
        "workflow_logs": ["Fell back to baseline interview profiles due to upstream connectivity faults."]
    }