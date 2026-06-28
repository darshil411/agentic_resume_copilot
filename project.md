Build a production-style AI Resume Tailoring & Interview Copilot focused heavily on LangGraph orchestration patterns, modular workflow design, HITL systems, checkpointing, parallel execution, and structured state management.

The goal is NOT to create a flashy UI-first app.
The goal is to demonstrate strong backend orchestration architecture using LangGraph + FastAPI.

The implementation should prioritize:

* clean state design
* modular nodes
* deterministic routing
* structured outputs
* checkpoint-safe execution
* resumability
* scalable graph architecture
* production-style folder structure
* beginner-readable but industry-style code

Avoid unnecessary complexity:

* no multi-agent chaos
* no unnecessary RAG
* no overengineering
* no huge abstractions initially

Core Stack:

* Python
* FastAPI
* LangGraph
* LangChain
* Pydantic
* PyMuPDF or pdfplumber
* OpenAI or Gemini
* LangSmith tracing
* Optional Tavily web search enrichment

==================================================
PROJECT OVERVIEW
================

The application should:

1. Accept:

   * resume PDF
   * job description text

2. Extract resume text

3. Convert raw text into structured Pydantic schema

4. Analyze the JD

5. Perform hybrid ATS evaluation:

   * deterministic keyword/skill matching
   * semantic LLM reasoning

6. Launch parallel workflow branches:

   * Resume Optimization Pipeline
   * Interview Preparation Pipeline
   * Outreach Generation Pipeline

7. Resume pipeline must include:

   * HITL approval
   * interrupts
   * checkpointing
   * resumability
   * retry loops
   * conditional routing

8. Final system should support:

   * HTML preview
   * PDF/DOCX export
   * interview prep export
   * outreach export

==================================================
IMPORTANT ARCHITECTURE DECISIONS
================================

The system should be designed as:

* DAG-style orchestration
* stateful execution engine
* NOT simple sequential chains

LangGraph concepts that MUST be demonstrated:

* StateGraph
* typed state
* reducers
* conditional edges
* parallel fan-out
* subgraphs
* interrupts
* checkpoint persistence
* resumability
* async-safe orchestration

==================================================
CORE EXECUTION FLOW
===================

START
↓
resume_upload_node
↓
resume_extraction_node
↓
resume_structuring_node
↓
jd_analysis_node
↓
ats_evaluation_node
↓

FAN-OUT INTO 3 PARALLEL BRANCHES:

1. Resume Optimization Pipeline
2. Interview Preparation Pipeline
3. Outreach Generation Pipeline

All branches should execute independently.

Resume branch is long-running HITL workflow.
Interview and outreach branches should complete independently and faster.

After all relevant branches complete:
↓
final_dashboard_node
↓
END

==================================================
GLOBAL SHARED STATE
===================

Use strict Pydantic-based graph state.

Global shared state should include:

```python
resume_text: str

job_description_text: str

original_resume: StructuredResume

optimized_resume: StructuredResume | None

jd_analysis: JDAnalysis

ats_report: ATSReport

workflow_logs: list[str]

branch_status: dict

errors: list[str]
```

==================================================
LOCAL SUBGRAPH STATES
=====================

Resume Pipeline Local State:

```python
current_section: str

proposed_changes: dict

approval_state: dict

section_retry_counts: dict

resume_export_paths: dict
```

Interview Pipeline Local State:

```python
company_research: dict

interview_questions: list

interview_experiences: list

prep_roadmap: list

interview_export_paths: dict
```

Outreach Pipeline Local State:

```python
cold_emails: list

referral_templates: list

followup_templates: list

outreach_export_paths: dict
```

==================================================
Pydantic MODELS
===============

Implement strongly typed schemas.

Examples:

```python
class Section(str, Enum):
    SUMMARY = "summary"
    SKILLS = "skills"
    PROJECTS = "projects"
    EXPERIENCE = "experience"


class Project(BaseModel):
    title: str
    description: str
    technologies: List[str]
    impact: str | None = None


class Experience(BaseModel):
    company: str
    role: str
    duration: str
    bullets: List[str]


class StructuredResume(BaseModel):
    summary: str
    skills: List[str]
    projects: List[Project]
    experience: List[Experience]
    education: List[str]
    certifications: List[str]


class JDAnalysis(BaseModel):
    required_skills: List[str]
    responsibilities: List[str]
    keywords: List[str]
    tools: List[str]
    experience_requirements: List[str]


class ATSReport(BaseModel):
    score: float
    matched_skills: List[str]
    missing_skills: List[str]
    weak_sections: List[str]
    improvement_suggestions: List[str]
```

==================================================
NODE ARCHITECTURE
=================

Each node should clearly define:

* what it reads from state
* what it writes
* deterministic vs LLM behavior
* possible failure modes

==================================================
FOUNDATION NODES
================

1. resume_upload_node

* stores uploaded file path
* stores JD text

2. resume_extraction_node
   Reads:

* uploaded PDF

Writes:

* resume_text

Deterministic node.

Must handle:

* corrupted PDFs
* empty PDFs
* extraction failures

3. resume_structuring_node
   Reads:

* resume_text

Writes:

* original_resume

LLM-based structured extraction.

Must:

* use structured outputs
* validate with Pydantic
* retry on malformed outputs

4. jd_analysis_node
   Reads:

* job_description_text

Writes:

* jd_analysis

LLM structured extraction.

5. ats_evaluation_node

IMPORTANT:
This must be HYBRID.

Deterministic layer:

* keyword overlap
* exact skill matching
* ATS heuristics

Semantic LLM layer:

* transferable skills
* semantic project alignment
* contextual fit

Writes:

* ats_report

==================================================
PARALLEL FAN-OUT
================

After ATS evaluation:
launch 3 parallel subgraphs using LangGraph fan-out patterns.

==================================================
RESUME OPTIMIZATION PIPELINE
============================

This is the MOST IMPORTANT branch.

Must demonstrate:

* conditional routing
* HITL
* interrupts
* checkpointing
* resumability
* retry loops

Flow:

optimization_router_node
↓
optimize_section_node
↓
approval_interrupt_node
↓
approval_processing_node
↓
route_after_approval

Possible routes:

* commit_changes_node
* regenerate optimize_section_node
* escalation_node

After approved changes:
↓
recompute_ats_node
↓
next weak section
↓
resume_export_node

==================================================
IMPORTANT APPROVAL DESIGN
=========================

Optimization nodes MUST NOT directly mutate optimized_resume.

Correct lifecycle:

proposal generation
→ proposed_changes
→ human approval
→ commit_changes_node
→ optimized_resume updated

==================================================
INTERRUPT + CHECKPOINT DESIGN
=============================

The graph must:

* pause during approval
* save checkpoint
* resume from checkpoint after human response

Demonstrate:

* interrupt()
* persistence
* resumability

==================================================
ROUTING RULES
=============

Routers must:

* remain deterministic
* NOT use LLMs
* NOT mutate state
* only inspect state and choose next node

Routing conditions:

* approval status
* retry count
* completion status

==================================================
RETRY STRATEGY
==============

Retry counts should be section-scoped.

Example:

```python
section_retry_counts = {
    "projects": 2
}
```

After retry limit:
route to escalation node.

==================================================
INTERVIEW PIPELINE
==================

Independent fast branch.

Should use:

* original_resume
* jd_analysis
* optional Tavily company research

Generate:

* technical questions
* behavioral questions
* project discussion prompts
* likely interview rounds
* preparation roadmap
* interview experiences/tips

This branch should NOT depend on optimized_resume.
It must remain independently parallelizable.

==================================================
OUTREACH PIPELINE
=================

Independent fast branch.

Generate:

* cold outreach emails
* referral requests
* recruiter followups

Optional Tavily enrichment:

* company context
* recent company news

==================================================
CHECKPOINTING STRATEGY
======================

Checkpoint after:

* expensive LLM nodes
* fan-out boundaries
* before/after interrupts
* approval commits

Checkpoint-after-every-node is acceptable for simplicity.

Do NOT store huge binary artifacts directly in graph state.
Store file paths/references only.

==================================================
REDUCERS
========

Demonstrate reducers for merge-safe parallel updates.

Important:
parallel branches may update same keys.

Reducers should be implemented where appropriate.

Examples:

* append workflow logs
* merge interview results
* merge generated outreach templates

Avoid reducers for canonical replace fields like:

* ats_report
* optimized_resume

==================================================
FOLDER STRUCTURE
================

Use clean modular architecture.

Suggested:

```text
app/
│
├── api/
├── graph/
│   ├── state/
│   ├── nodes/
│   ├── routers/
│   ├── subgraphs/
│   ├── reducers/
│   ├── checkpoints/
│   └── builders/
│
├── models/
├── services/
├── prompts/
├── exporters/
├── utils/
└── main.py
```

==================================================
IMPLEMENTATION STYLE
====================

Code must:

* explain WHY each component exists
* include comments for LangGraph concepts
* remain modular
* avoid giant files
* be interview-quality
* beginner-readable
* production-inspired

==================================================
IMPORTANT ENGINEERING PRINCIPLES
================================

Prioritize:

* understandable orchestration
* workflow correctness
* state consistency
* clean graph flow
* safe resumability
* deterministic routing
* modular node contracts

Avoid:

* prompt spaghetti
* giant god-state objects
* uncontrolled shared mutation
* unnecessary agents
* unnecessary RAG
* random abstractions

==================================================
VERY IMPORTANT
==============

Do NOT dump one giant monolithic file.

Build incrementally.

Start with:

1. Pydantic schemas
2. GraphState
3. Basic nodes
4. Routing functions
5. Foundation graph
6. Resume HITL subgraph
7. Parallel branches
8. Persistence/checkpointing
9. Export layer

Include:

* detailed explanations
* architectural reasoning
* tradeoff explanations
* debugging tips
* common beginner mistakes
* LangGraph best practices

This project is intended to deeply teach:

* LangGraph orchestration
* workflow systems
* checkpointing
* interrupts
* reducers
* state design
* production AI backend architecture
* DAG thinking
* async orchestration
* HITL systems
* modular AI engineering
