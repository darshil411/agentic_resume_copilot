from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class ATSCategoryScores(BaseModel):
    """
    Category-level breakdown of an ATS evaluation.

    New fields (Phase 2.3A — deterministic engine):
        skill_match          : 0–100, deterministic exact+alias skill coverage
        semantic_alignment   : 0–100, placeholder (Phase 2.3B)
        quantified_impact    : 0–100, placeholder (Phase 2.3C)
        penalties            : 0–10,  placeholder (Phase 2.3C)

    Legacy fields (kept for backward compatibility with foundation_nodes.py
    which constructs ATSCategoryScores directly using the old schema and which
    is out of scope to modify in this phase).  They are all Optional with a
    default of 0.0 so they do not need to be supplied by the new engine.
    """
    # ── New engine fields ──────────────────────────────────────────────────
    skill_match: float = Field(
        default=0.0,
        description="Deterministic skill coverage score (0–100)"
    )
    semantic_alignment: float = Field(
        default=0.0,
        description="Semantic alignment score (0–100). Placeholder until Phase 2.3B."
    )
    quantified_impact: float = Field(
        default=0.0,
        description="Quantified-impact score (0–100). Placeholder until Phase 2.3C."
    )
    semantic_error: Optional[str] = Field(
        default=None,
        description="Status/error message if the semantic model fails (e.g., unavailable)"
    )

    # ── Legacy fields — retained so foundation_nodes.py keeps compiling ───
    # foundation_nodes._build_fallback_ats_report supplies all of these.
    keyword_match: float = Field(
        default=0.0,
        description="[Legacy] Out of 30 — used by foundation_nodes fallback only"
    )
    experience_alignment: float = Field(
        default=0.0,
        description="[Legacy] Out of 15 — used by foundation_nodes fallback only"
    )
    project_relevance: float = Field(
        default=0.0,
        description="[Legacy] Out of 15 — used by foundation_nodes fallback only"
    )
    quantifiable_impact: float = Field(
        default=0.0,
        description="[Legacy] Out of 10 — used by foundation_nodes fallback only"
    )
    resume_structure: float = Field(
        default=0.0,
        description="[Legacy] Out of 10 — used by foundation_nodes fallback only"
    )
    writing_quality: float = Field(
        default=0.0,
        description="[Legacy] Out of 10 — used by foundation_nodes fallback only"
    )
    penalties: float = Field(
        default=0.0,
        description="Penalty points (0–10). Negative impact from stuffing / repetition."
    )


class ATSReport(BaseModel):
    """
    Top-level ATS evaluation report.

    Required by:
      - GlobalGraphState (ats_report / optimized_ats_report)
      - resume_nodes.optimize_section_node (reads .missing_skills)
      - ExportWorkspace.jsx (reads .score, .missing_skills)
      - foundation_nodes (LLM structured output + fallback builder)

    New fields that the deterministic engine (ats_engine.py) populates:
        score           — temporarily set to skill_match until all components exist
        matched_skills  — canonical matched skill names
        missing_skills  — JD skills absent from the resume

    Legacy fields retained because foundation_nodes.py constructs them
    and they are not in scope to remove this phase:
        weak_sections, improvement_priorities, optimization_guidelines,
        overall_feedback
    """
    score: float = Field(description="Final ATS Score (0-100)")
    is_fallback_score: bool = Field(
        default=False,
        description="True if the semantic model was unavailable and the score is a partial fallback"
    )
    category_scores: ATSCategoryScores

    matched_skills: List[str] = Field(
        default_factory=list,
        description="Canonical skill names present in both JD and resume"
    )
    missing_skills: List[str] = Field(
        default_factory=list,
        description="JD skills absent from the resume (human-readable)"
    )

    # ── Legacy fields — foundation_nodes fallback builder populates these ─
    weak_sections: List[str] = Field(
        default_factory=list,
        description="[Legacy] Resume sections needing improvement"
    )
    improvement_priorities: List[str] = Field(
        default_factory=list,
        description="[Legacy] Ranked improvement actions"
    )
    optimization_guidelines: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="[Legacy] Per-section guidelines for downstream agents"
    )
    overall_feedback: List[str] = Field(
        default_factory=list,
        description="[Legacy] Max 5 concise feedback bullets"
    )
