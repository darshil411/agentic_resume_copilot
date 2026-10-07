# PROJECT MEMORY — AI Resume Tailoring & Interview Copilot

## 0. PROJECT IDENTITY

Project name:
AI Resume Tailoring & Interview Copilot

Repository:
https://github.com/darshil411/agentic_resume_copilot

Current active frontend branch:
react

Primary purpose:
Build an AI-assisted career workflow that takes a candidate's resume + target Job Description + optional detailed project documents and produces:
1. Structured resume analysis
2. JD analysis
3. ATS evaluation
4. Section-by-section resume optimization with Human-in-the-Loop approval
5. Interview preparation material
6. Company/interview research
7. Cold email templates
8. Referral templates
9. Follow-up templates
10. Final optimized resume/export artifacts

Core design principle:
The system should not allow an LLM to blindly rewrite the complete resume.
The resume is optimized section-by-section and each generated change passes through Human-in-the-Loop approval.

---

# 1. CURRENT TECHNOLOGY STACK

## Backend

Python
FastAPI
LangGraph
LangChain
Pydantic
PyMuPDF
SQLite
LangGraph SQLite Checkpointer
ThreadPoolExecutor
python-dotenv

## LLM providers

OpenRouter
Cerebras
Groq
Google Gemini

Provider assignment currently used by the code:

OpenRouter:
- resume_structuring_node
- jd_analysis_node
- ats_evaluation_node
- project selection

Cerebras:
- resume section optimization

Groq:
- interview preparation
- outreach generation

Gemini:
- fallback provider
- Gemini key rotation
- project context compression

## External research

Tavily is used for web/company/interview research in the interview-preparation workflow.

## Frontend

React
Vite
React Router
Tailwind CSS
Lucide React

The frontend communicates with FastAPI through REST APIs.

## Observability

LangSmith is included in the backend stack and LLM calls use tracing/tags where implemented.

---

# 2. HIGH-LEVEL ARCHITECTURE

The system is divided into:

Frontend
    ↓
FastAPI API layer
    ↓
LangGraph orchestration
    ↓
Foundation processing
    ↓
Resume optimization workflow
    +
Interview background workflow
    +
Outreach background workflow
    ↓
Final results / exports

The frontend does NOT directly call LLM providers.

FastAPI is the boundary between frontend and backend.

LangGraph owns the main resume workflow and persistent workflow state.

---

# 3. CURRENT REQUEST FLOW

A user submits:

- Resume PDF
- Job Description
- Optional project documents

The request enters:

POST /api/v1/workflow/start

The API:

1. Saves the resume to data/uploads/
2. Validates optional project documents
3. Extracts project-document text
4. If project documents exist:
   - selects the most relevant projects
   - compresses them into project context
5. Creates a unique thread_id
6. Initializes background result slots
7. Creates initial LangGraph state
8. Starts graph execution through a FastAPI background task

Initial graph state includes:

resume_file_path
job_description_text
selected_project_context
workflow_logs
errors
current_section
branch_status

---

# 4. MAIN LANGGRAPH FLOW

Current main graph:

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
trigger_background_workers_node
  ↓
resume_subgraph
  ↓
final_ats_node
  ↓
final_dashboard_node
  ↓
END

Error routing exists around extraction and resume structuring.

Possible error paths:

resume_extraction_node
    ↓
route_on_errors
    ├── continue
    ├── parsing_error_node
    └── escalation_node

resume_structuring_node
    ↓
route_on_errors
    ├── continue
    ├── schema_validation_retry_node
    └── escalation_node

schema_validation_retry_node
    ↓
resume_structuring_node

---

# 5. FOUNDATION NODES

Location:

app/graph/nodes/foundation_nodes.py

## resume_upload_node

Purpose:
Initial workflow initialization.

Input:
GlobalGraphState

Important:
The actual file is already saved by FastAPI before the graph starts.

Output:
workflow_logs

---

## resume_extraction_node

Purpose:
Extract raw text from uploaded resume PDF.

Technology:
PyMuPDF / fitz

Input:
resume_file_path

Output:
resume_text

This is deterministic.

It does NOT use an LLM.

Conceptually:

PDF
 ↓
PyMuPDF
 ↓
raw text
 ↓
state.resume_text

---

## resume_structuring_node

Purpose:
Convert raw resume text into the structured Pydantic resume representation.

Input:
resume_text

Output:
original_resume

Primary:
OpenRouter / gpt-4o-mini

Fallback:
Gemini

Structured output:
StructuredResume

If both providers fail:
static fallback resume structure is generated.

---

## jd_analysis_node

Purpose:
Understand the target Job Description.

Input:
job_description_text

Output:
jd_analysis

Primary:
OpenRouter / gpt-4o-mini

Fallback:
Gemini

Fallback:
static JD analysis if both providers fail.

---

## ats_evaluation_node

Purpose:
Evaluate how well the original structured resume matches the JD.

Inputs:

original_resume
jd_analysis

The implementation uses a hybrid approach.

Deterministic preprocessing:
- extracts resume skills
- serializes resume
- matches required skills
- calculates deterministic exact-match information
- identifies missing skills

LLM evaluation:
- keyword match
- experience alignment
- project relevance
- quantifiable impact
- structure
- writing quality
- penalties
- improvement priorities
- optimization guidelines

Output:

ats_report

Important:
ats_report is not only displayed to the user.

It is also consumed by downstream resume optimization.

Therefore its optimization_guidelines and missing_skills influence how individual resume sections are rewritten.

---

# 6. PROJECT KNOWLEDGE BASE

Project-document support is implemented in the API/service layer.

Files:

app/services/project_document_loader.py
app/services/project_context_service.py

Users can upload up to:

MAX_PROJECT_FILES = 5

Supported extensions:

.md
.txt
.pdf

## Project document flow

Uploaded project documents
        ↓
extract_text_from_file()
        ↓
raw project texts
        ↓
select_relevant_projects()
        ↓
top relevant projects
        ↓
build_project_context()
        ↓
compressed project knowledge
        ↓
GlobalGraphState.selected_project_context

---

## extract_text_from_file()

Location:

app/services/project_document_loader.py

Supports:
PDF
TXT
Markdown

PDF:
PyMuPDF

Text files:
UTF-8 with latin-1 fallback.

---

## select_relevant_projects()

Location:

app/services/project_context_service.py

Purpose:
When many project documents are uploaded, select the strongest 2–3 projects for the target JD.

The selection considers:

- technology overlap
- required frameworks
- domain similarity
- JD responsibilities
- architecture relevance
- production engineering
- APIs
- databases
- infrastructure
- scalability
- performance
- measurable achievements
- technical depth

Uses:
OpenRouter structured output.

Output:
selected project document texts.

---

## build_project_context()

Purpose:
Compress selected project documentation into an internal project knowledge base.

Uses:
Gemini structured output.

The context preserves:

- project identity
- business problem
- summary
- tech stack
- architecture
- engineering highlights
- responsibilities
- verified metrics
- ATS keywords

It removes irrelevant setup/documentation information.

The resulting context is injected into resume optimization, especially project optimization.

Important:
This is NOT traditional vector RAG.

It is:
document upload
→ relevance selection
→ context compression
→ injection into downstream LLM prompt.

---

# 7. RESUME OPTIMIZATION SUBGRAPH

Location:

app/graph/builders/resume_subgraph.py

The resume optimization loop is:

optimize_section_node
        ↓
approval_processing_node
        ↓
conditional routing
        ↓
commit_changes_node
        ↓
next section
        ↓
optimize_section_node

For each non-empty resume section:

1. Generate proposed improvement
2. Pause for human review
3. User approves / rejects / skips
4. If approved → commit
5. If rejected → regenerate
6. If retry limit exceeded → escalation
7. Continue to next non-empty section

Master section sequence:

summary
skills
experience
projects
education
certifications

Empty sections are automatically skipped.

---

# 8. optimize_section_node

Location:

app/graph/nodes/resume_nodes.py

Purpose:
Generate a proposal for one resume section.

Inputs include:

original_resume
optimized_resume
jd_analysis
ats_report
current_section
human_feedback
selected_project_context

Primary LLM:
Cerebras

Fallback:
Gemini

Structured output:
ProposedChanges

The output is stored in:

proposed_changes

Important:
This node does NOT directly overwrite the final resume.

It creates a proposal.

The human must approve the proposal before commit.

---

# 9. approval_processing_node

Purpose:
Human-In-the-Loop checkpoint.

Uses LangGraph interrupt().

Payload contains:

type:
resume_review

section:
current section

proposal:
generated changes

The graph pauses until the API resumes it.

Possible user actions:

approve
reject
skip

Approve:
approval_state[section] = approved

Reject:
approval_state[section] = rejected
human_feedback[section] = feedback
retry counter increases

Skip:
approval_state[section] = skipped

---

# 10. RESUME ROUTING LOGIC

Location:

app/graph/routers/resume_router.py

route_after_approval()

Rules:

If approved:
    → commit_changes_node

If skipped:
    → commit_changes_node

If retry count >= 2:
    → escalation_node

Otherwise:
    → optimize_section_node

Important:
The routing decision is deterministic.

The LLM does not decide whether the user approved the change.

The human controls approval.

---

# 11. commit_changes_node

Purpose:
Apply an approved section change to optimized_resume.

Important behavior:

If optimized_resume does not exist:
copy original_resume.

If proposal is approved:
replace only the current section.

Then determine the next non-empty section.

If all sections are complete:

current_section = DONE

Otherwise:

current_section = next non-empty section

This allows the workflow to skip missing sections.

---

# 12. STATE MODEL

Main state:

app/graph/state/global_state.py

GlobalGraphState is the central state contract.

## Input state

resume_file_path
job_description_text
selected_project_context

## Foundation state

resume_text
original_resume
jd_analysis
ats_report
optimized_ats_report
optimized_resume

## Resume HITL state

current_section
proposed_changes
approval_state
human_feedback
section_retry_counts
resume_export_paths

## Interview state

company_research
interview_questions
interview_experiences
prep_roadmap
interview_export_paths

## Outreach state

cold_emails
referral_templates
followup_templates
outreach_export_paths

## System state

workflow_logs
errors
branch_status

---

# 13. REDUCERS

Location:

app/graph/state/reducers.py

Two reducers exist.

## merge_dicts()

Used for dictionary state fields.

Behavior:

old dictionary
+
new dictionary
=
merged dictionary

Used for:

approval_state
human_feedback
section_retry_counts
branch_status

Reason:
Multiple workflow updates should not erase previously stored dictionary entries.

---

## append_list()

Used for:

workflow_logs
errors

Behavior:
append new list values to existing list.

---

# 14. CHECKPOINTING

Location:

app/utils/sqlite_checkpoint.py

Preferred:

SqliteSaver

Database:

data/checkpoints.sqlite

SQLite configuration:

WAL mode
synchronous=NORMAL

Reason:
The application has API reads and graph/background execution happening around the same workflow state.

Fallback:

MemorySaver

Important:
MemorySaver loses state when the process restarts.

Production deployment should use persistent SQLite storage or migrate to a production database/checkpointer.

---

# 15. LLM FACTORY

Location:

app/utils/llm_factory.py

Purpose:
Centralize LLM provider creation.

Supported providers:

openrouter
cerebras
groq
gemini

## OpenRouter

Default:
openai/gpt-4o-mini

Used for:
resume structuring
JD analysis
ATS evaluation
project selection

## Cerebras

Default:
gpt-oss-120b

Used for:
resume section optimization

## Groq

Default:
openai/gpt-oss-120b

Used for:
interview preparation
outreach

## Gemini

Default:
gemini-2.5-flash

Used as:
fallback provider

Gemini supports multiple API keys:

GEMINI_API_KEY
GEMINI_API_KEY_2
GEMINI_API_KEY_3

The factory rotates keys when quota exhaustion / 429 occurs.

---

# 16. INTERVIEW PREPARATION

Location:

app/graph/nodes/interview_nodes.py

The interview workflow generates information such as:

company research
interview experiences
company-specific questions
tailored technical questions
preparation roadmap

It uses:

original_resume
jd_analysis

and external web research through Tavily.

The objective is not simply to generate generic interview questions.

It tries to provide:

- what the company does
- relevant company information
- interview experiences
- likely question categories
- project-specific questions
- preparation guidance

The branch has fallback behavior if external/LLM calls fail.

---

# 17. OUTREACH

Location:

app/graph/nodes/outreach_nodes.py

Purpose:
Generate:

cold emails
referral messages
follow-up messages

Inputs:

original_resume
jd_analysis

Primary:
Groq

Fallback:
Gemini

Hard fallback:
generic predefined templates

This branch is independent of the resume optimization loop.

---

# 18. BACKGROUND WORKERS

Location:

app/workers/background_jobs.py

The system maintains an in-process result store:

_bg_results

Each workflow gets:

interview status
outreach status

Possible status:

PROCESSING
COMPLETED
FAILED

The workers create a lightweight GlobalGraphState containing:

original_resume
jd_analysis

and invoke the corresponding node functions.

Important:
Interview/outreach results are currently stored in process memory.

They are NOT the same as the persistent LangGraph checkpoint.

Therefore:
server restart = background result memory is lost.

---

# 19. FASTAPI API LAYER

Main API file:

app/api/routes.py

Router prefix:

/api/v1

Important endpoint:

POST /api/v1/workflow/start

Inputs:

resume
job_description
optional project_docs

Returns:

thread_id
status

---

Workflow status:

GET /api/v1/workflow/{thread_id}

Returns:

overall status
branch statuses
current review section
ATS report
optimized ATS report
workflow logs

---

Current review task:

GET /api/v1/resume/task/current/{thread_id}

Used by frontend to retrieve:

current section
proposal
reasoning
original section
approval state
interrupt state

---

# 20. HITL RESUME API

The API uses LangGraph Command to resume interrupted workflows.

Important concurrency protection:

_thread_locks

A lock is maintained per thread_id.

Purpose:
Prevent duplicate resume commands caused by repeated UI actions / requests.

The graph is resumed with:

Command(resume=...)

The API then checks the graph state again.

---

# 21. FRONTEND RESPONSIBILITY

Frontend:

frontend-react/

Technology:

React
Vite
React Router
Tailwind
Lucide

Frontend responsibility:

- upload resume
- enter JD
- upload project documents
- display workflow status
- display resume sections
- show AI proposals
- allow approve/reject/skip
- display interview preparation
- display outreach
- display exports
- poll backend workflow state

Frontend does NOT own workflow logic.

FastAPI + LangGraph remain the source of truth.

---

# 22. FILE RESPONSIBILITY MAP

app/
├── main.py
│   └── FastAPI application initialization + CORS + route registration
│
├── api/
│   ├── routes.py
│   │   └── HTTP API + workflow lifecycle + HITL resume commands
│   │
│   └── dtos/
│       └── API response/request contracts
│
├── graph/
│   ├── state/
│   │   ├── global_state.py
│   │   └── reducers.py
│   │
│   ├── builders/
│   │   ├── main_graph.py
│   │   └── resume_subgraph.py
│   │
│   ├── nodes/
│   │   ├── foundation_nodes.py
│   │   ├── resume_nodes.py
│   │   ├── interview_nodes.py
│   │   ├── outreach_nodes.py
│   │   └── error_nodes.py
│   │
│   └── routers/
│       ├── resume_router.py
│       └── error_router.py
│
├── models/
│   ├── resume.py
│   ├── jd.py
│   └── ats.py
│
├── services/
│   ├── project_document_loader.py
│   └── project_context_service.py
│
├── workers/
│   └── background_jobs.py
│
└── utils/
    ├── llm_factory.py
    └── sqlite_checkpoint.py

frontend-react/
├── package.json
├── src/
└── public/

data/
├── uploads/
└── checkpoints.sqlite

---

# 23. IMPORTANT DESIGN PRINCIPLES

## Separation of concerns

FastAPI:
API boundary

LangGraph:
workflow orchestration

Nodes:
individual processing units

Routers:
deterministic workflow decisions

Pydantic models:
structured data contracts

LLM factory:
provider abstraction

Services:
document/project processing

Workers:
independent long-running supplementary tasks

Frontend:
presentation + user interaction

---

# 24. IMPORTANT NON-GOALS

The system must NOT:

- invent candidate experience
- invent skills
- invent projects
- invent metrics
- create fake achievements
- allow LLM to approve its own resume changes
- treat keyword stuffing as genuine optimization
- blindly replace the entire resume
- depend on project documentation to invent resume content

---

# 25. CURRENT ATS DESIGN

ATS evaluation is hybrid.

Deterministic layer:
- extracts required skills
- detects exact matches
- identifies missing skills
- provides objective keyword signals

LLM layer:
- evaluates semantic relevance
- evaluates experience alignment
- evaluates project relevance
- evaluates measurable impact
- evaluates structure
- evaluates writing quality
- identifies weaknesses
- produces optimization guidance

The ATS report feeds the optimization workflow.

Therefore ATS evaluation is not just a UI score.

It is a planning signal for downstream optimization.

---

# 26. CURRENT ATS RUBRIC

Current conceptual weighting:

Keyword Match:
30

Experience Alignment:
15

Project Relevance:
15

Quantifiable Impact:
10

Resume Structure:
10

Writing Quality:
10

Keyword Stuffing Penalty:
up to -5

Repetition Penalty:
up to -5

Important:
The score is an internal composite evaluation.
It is NOT claimed to reproduce a commercial ATS vendor's proprietary score.

---

# 27. OPTIMIZATION SAFETY RULE

Resume optimization should improve presentation and JD alignment using existing evidence.

Allowed:
- better wording
- stronger action verbs
- better ordering
- natural JD keyword alignment
- clearer technical descriptions
- better project relevance
- using verified information from Project Knowledge Base

Not allowed:
- fabricated technologies
- fabricated metrics
- fabricated experience
- fabricated responsibilities
- fabricated projects

---

# 28. ERROR / FALLBACK STRATEGY

The project uses multiple layers of failure handling.

LLM provider failure:
→ fallback provider

Gemini quota:
→ rotate Gemini API keys

Structured-output failure:
→ validation/error routing or fallback

PDF extraction failure:
→ parsing error route

Resume optimization failure:
→ errors + retry through HITL

Repeated section rejection:
→ retry limit
→ escalation

Interview/outreach failure:
→ branch-specific fallback

---

# 29. IMPORTANT CURRENT IMPLEMENTATION CAVEATS

1. Background interview/outreach results are stored in process memory.

2. SQLite is appropriate for the current deployment architecture but requires persistent storage.

3. MemorySaver fallback should not be used for production persistence.

4. The project-context system is contextual document selection/compression, not a vector database RAG system.

5. The main resume workflow is the LangGraph workflow.
Interview/outreach currently run through background worker functions rather than being represented as LangGraph subgraphs.

6. Frontend and backend are separate deployments.

7. CORS is environment-driven through:
CORS_ORIGINS

8. The backend creates:
data/uploads
data/

on startup.

9. Uploaded project documents are deleted after their text is extracted and processed.

10. Resume uploads remain under data/uploads unless explicitly cleaned.

---

# 30. ENVIRONMENT VARIABLES

LLM:

OPENROUTER_API_KEY
CEREBRAS_API_KEY
GROQ_API_KEY
GEMINI_API_KEY
GEMINI_API_KEY_2
GEMINI_API_KEY_3

Optional Google alias:

GOOGLE_API_KEY

Research:

TAVILY_API_KEY

Observability:

LangSmith-related environment variables as configured locally/deployment.

API:

CORS_ORIGINS

---

# 31. DEBUGGING MENTAL MODEL

When something fails, trace in this order:

Frontend
 ↓
API endpoint
 ↓
initial state
 ↓
LangGraph state
 ↓
node
 ↓
LLM/provider/service
 ↓
state update
 ↓
router
 ↓
next node
 ↓
frontend polling

For resume issues:

Check:
resume_file_path
→ resume_text
→ original_resume
→ jd_analysis
→ ats_report
→ current_section
→ proposed_changes
→ approval_state
→ optimized_resume

For HITL issues:

Check:
thread_id
→ checkpoint
→ current graph state
→ interrupt payload
→ approval command
→ thread lock
→ graph resume

For ATS issues:

Check:
original_resume
→ deterministic matching
→ LLM rubric
→ ATSReport
→ optimization_guidelines
→ optimize_section_node

For project-context issues:

Check:
uploaded documents
→ extraction
→ project selection
→ context compression
→ selected_project_context
→ projects optimization prompt

---

# 32. CORE INTERVIEW EXPLANATION

Business explanation:

"This is an AI Resume Tailoring and Interview Copilot. A user provides their resume and a target job description, and the system analyzes the match, evaluates ATS alignment, and then improves the resume section by section with human approval. At the same time, it can research the company and generate interview preparation material and outreach templates. Users can also upload detailed project documentation so the system can select and use the most relevant project evidence instead of relying only on the short project descriptions in the resume."

Technical explanation:

"The backend is built around FastAPI and LangGraph. FastAPI handles the API and workflow lifecycle, while LangGraph manages the stateful resume optimization workflow. The initial pipeline extracts the resume, structures it into Pydantic models, analyzes the JD, and generates an ATS report. The resume then enters a HITL subgraph where each non-empty section is optimized, paused for user approval, committed if approved, or regenerated if rejected. Interview and outreach generation run as separate background workers. LLM provider access is centralized through an LLM factory with provider-specific models and fallbacks. SQLite checkpointing preserves LangGraph state."

---

# 33. IMPORTANT TERMINOLOGY

"State":
The shared data object passed between LangGraph nodes.

"Node":
A Python function that performs one unit of work.

"Router":
A deterministic function that decides which graph edge to follow.

"Reducer":
Defines how multiple updates to the same state field are merged.

"Checkpoint":
Persisted snapshot of graph state that allows workflow continuation.

"Interrupt":
LangGraph mechanism that pauses execution for human input.

"HITL":
Human-In-The-Loop; the human controls whether generated resume changes are accepted.

"Project Knowledge Base":
Compressed context extracted from uploaded project documentation and injected into optimization.

"ATS Report":
Structured evaluation of resume-to-JD alignment used both for display and downstream optimization.

"Background Worker":
Separate in-process execution for interview/outreach generation so the main resume workflow does not have to synchronously wait for those results.

---

# 34. RULE FOR FUTURE AI AGENTS

Before modifying this project:

1. Read GlobalGraphState first.
2. Trace the relevant graph builder.
3. Trace the node.
4. Trace its router if applicable.
5. Check the Pydantic model used by the node.
6. Check API routes if the change affects frontend behavior.
7. Check reducers if changing state fields.
8. Check checkpointing if changing persistence.
9. Do not assume the old architecture from previous conversations is still correct.
10. Treat the current repository code as the source of truth.
11. Do not invent files/functions that are not present.
12. Preserve existing HITL behavior unless explicitly asked to change it.
13. Preserve factual integrity of resume generation.
14. Avoid moving LLM calls into FastAPI routes.
15. Avoid introducing unnecessary abstractions.

END OF PROJECT MEMORY