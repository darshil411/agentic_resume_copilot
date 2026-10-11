"""
app/services/ats_engine.py
--------------------------
Phase 2.3A — Deterministic skill extraction and matching.

Public interface
    evaluate_resume(resume: StructuredResume, jd_analysis: JDAnalysis) -> ATSReport

This module is intentionally independent of:
    LangGraph, FastAPI, frontend, network, LLMs.

Phase completion state
    skill_match        — IMPLEMENTED (Phase 2.3A)
    semantic_alignment — IMPLEMENTED (Phase 2.3B)
    quantified_impact  — IMPLEMENTED (Phase 2.3C)
    penalties          — IMPLEMENTED (Phase 2.3D)
    score              — IMPLEMENTED (final weighted formula)
"""

from __future__ import annotations

import logging
import math
import re
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

from app.models.ats import ATSCategoryScores, ATSReport
from app.models.jd import JDAnalysis
from app.models.resume import StructuredResume

# ---------------------------------------------------------------------------
# Alias table
# ---------------------------------------------------------------------------
# Format:  canonical_name  →  frozenset of all normalized spellings that map
#          to it (canonical_name itself must be included in the set).
#
# Keys are the authoritative names returned in matched_skills.
# All values are in the form produced by _normalize_raw() BEFORE alias lookup.
#
# _normalize_raw steps:
#   1. lowercase
#   2. strip surrounding whitespace
#   3. replace separator chars (. - / # +) with space
#   4. collapse repeated whitespace
#   5. replace remaining spaces with underscore
#   (alias lookup applied afterwards)
#
# Trace for selected inputs (do NOT edit these without re-tracing):
#   "PostgreSQL"          → "postgresql"
#   "Postgres"            → "postgres"
#   "pg"                  → "pg"
#   "React"               → "react"
#   "React.js"            → "react_js"   (dot → space → underscore)
#   "ReactJS"             → "reactjs"
#   "REST API"            → "rest_api"
#   "RESTful API"         → "restful_api"
#   "scikit-learn"        → "scikit_learn"
#   "sklearn"             → "sklearn"
#   "AWS"                 → "aws"
#   "Amazon Web Services" → "amazon_web_services"
#   "K8s"                 → "k8s"
#   "Kubernetes"          → "kubernetes"
#   "Node.js"             → "node_js"
#   "Node"                → "node"
#   "NodeJS"              → "nodejs"

_CANONICAL_ALIASES: Dict[str, FrozenSet[str]] = {
    "postgresql": frozenset({"postgresql", "postgres", "pg"}),
    "react":      frozenset({"react", "react_js", "reactjs"}),
    "rest_api":   frozenset({"rest_api", "restful_api", "rest_apis", "restful_apis"}),
    "scikit_learn": frozenset({"scikit_learn", "sklearn"}),
    "aws":        frozenset({"aws", "amazon_web_services"}),
    "kubernetes": frozenset({"kubernetes", "k8s"}),
    "nodejs":     frozenset({"nodejs", "node_js", "node"}),
}

# Flat reverse lookup: normalized_raw → canonical  (built from _CANONICAL_ALIASES)
_NORM_TO_CANONICAL: Dict[str, str] = {}
for _canon, _aliases in _CANONICAL_ALIASES.items():
    for _alias in _aliases:
        _NORM_TO_CANONICAL[_alias] = _canon


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def _normalize_raw(raw: str) -> str:
    """Normalize a skill string WITHOUT applying alias lookup.

    Steps:
        1. lowercase
        2. strip surrounding whitespace
        3. replace separator chars (., -, /, #, +) with a single space
        4. collapse repeated whitespace
        5. strip again
        6. replace internal spaces with underscore (multi-word → single token)
    """
    s = raw.lower().strip()
    s = re.sub(r"[.\-/#+]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s.replace(" ", "_")


def _normalize_skill(raw: str) -> str:
    """Full normalization: _normalize_raw then alias lookup.

    Returns the canonical name if the input is a known alias,
    otherwise returns the normalized raw form.
    """
    normed = _normalize_raw(raw)
    return _NORM_TO_CANONICAL.get(normed, normed)


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def _phrase_pattern(normalized_phrase: str) -> str:
    """Return a regex pattern that matches the phrase as whole words.

    normalized_phrase is underscore-joined (e.g. "rest_api", "machine_learning").
    The pattern uses word boundaries and allows flexible whitespace between words.

    Examples:
        "restapi"          → r"\\brestapi\\b"       (single word, no split)
        "rest_api"         → r"\\brest\\s+api\\b"
        "machine_learning" → r"\\bmachine\\s+learning\\b"
    """
    words = normalized_phrase.split("_")
    return r"\b" + r"\s+".join(re.escape(w) for w in words) + r"\b"


def _matches_in_text(normalized_phrase: str, text_lower: str) -> bool:
    """Return True if normalized_phrase appears as whole words in text_lower."""
    return bool(re.search(_phrase_pattern(normalized_phrase), text_lower))


def _all_alias_patterns(canonical: str) -> List[str]:
    """Return all normalized alias forms for a canonical name."""
    return list(_CANONICAL_ALIASES.get(canonical, {canonical}))


# ---------------------------------------------------------------------------
# Resume skill extraction — NO JSON dump tokenization
# ---------------------------------------------------------------------------

def _extract_explicit_skills(resume: StructuredResume) -> Set[str]:
    """Extract canonical skills from the StructuredSkills block only.

    Each skill string is normalized directly (not tokenized) so multi-word
    skill names like "Machine Learning" survive intact as "machine_learning".
    """
    canonical: Set[str] = set()
    if not resume.skills:
        return canonical
    skill_lists = [
        resume.skills.languages,
        resume.skills.frameworks,
        resume.skills.tools,
        resume.skills.databases,
        resume.skills.concepts,
    ]
    for group in skill_lists:
        for raw in (group or []):
            if isinstance(raw, str) and raw.strip():
                canonical.add(_normalize_skill(raw))
    return canonical


def _extract_tech_stack_skills(resume: StructuredResume) -> Set[str]:
    """Extract canonical skills from project tech_stack lists only."""
    canonical: Set[str] = set()
    for proj in (resume.projects or []):
        for tech in (proj.tech_stack or []):
            if isinstance(tech, str) and tech.strip():
                canonical.add(_normalize_skill(tech))
    return canonical


def _all_freeform_text(resume: StructuredResume) -> str:
    """Return all freeform resume text in a single lowercased string.

    Includes: experience bullets, experience role, project descriptions,
    project titles.  Does NOT include schema keys or JSON structure.
    """
    parts: List[str] = []
    for exp in (resume.experience or []):
        if exp.role:
            parts.append(exp.role)
        if exp.company:
            parts.append(exp.company)
        parts.extend(exp.bullets or [])
    for proj in (resume.projects or []):
        if proj.title:
            parts.append(proj.title)
        if proj.description:
            parts.append(proj.description)
    return " ".join(parts).lower()


# ---------------------------------------------------------------------------
# Skill match
# ---------------------------------------------------------------------------

def _compute_skill_match(
    resume: StructuredResume,
    jd_analysis: JDAnalysis,
) -> Tuple[float, List[str], List[str]]:
    """Return (skill_match_score, matched_skills, missing_skills).

    skill_match_score : float in [0.0, 100.0], unrounded
    matched_skills    : sorted list of canonical names
    missing_skills    : sorted list of original JD skill strings

    Matching strategy (in order, first match wins):
        1. Direct canonical set match against explicit StructuredSkills
        2. Direct canonical set match against project tech_stack
        3. Phrase/alias search in all freeform text (experience bullets,
           project descriptions/titles) — checks EVERY alias of the
           canonical, not just the canonical form itself.

    Word-boundary protection:
        _phrase_pattern() generates word-boundary anchors so:
            "C"       does not match "CSS"
            "React"   does not match "Reaction"
            "Go"      does not match "Google"
            "Machine Learning" matches "machine learning pipeline" ✓
            "RESTful API" alias of rest_api matches "RESTful API" in text ✓
    """
    # Map canonical → original JD string (deterministic: first occurrence wins)
    jd_canonical_to_original: Dict[str, str] = {}
    for raw_skill in (jd_analysis.required_skills or []):
        if raw_skill and raw_skill.strip():
            canon = _normalize_skill(raw_skill)
            if canon not in jd_canonical_to_original:
                jd_canonical_to_original[canon] = raw_skill

    if not jd_canonical_to_original:
        return 0.0, [], []

    # Pre-compute resume skill sets
    explicit_skills  = _extract_explicit_skills(resume)
    tech_stack_skills = _extract_tech_stack_skills(resume)
    resume_canonical = explicit_skills | tech_stack_skills

    # Pre-compute combined freeform text (lowercased once)
    freeform = _all_freeform_text(resume)

    matched_canonical: Set[str] = set()
    missing_originals: List[str] = []

    for canon, original in sorted(jd_canonical_to_original.items()):
        # 1. Direct canonical match (explicit skills or tech_stack)
        if canon in resume_canonical:
            matched_canonical.add(canon)
            continue

        # 2. Any alias in explicit skills or tech_stack
        aliases = _all_alias_patterns(canon)
        if any(a in resume_canonical for a in aliases):
            matched_canonical.add(canon)
            continue

        # 3. Phrase/alias search in freeform text
        #    Check every alias form (including canonical itself) as a phrase.
        if freeform and any(_matches_in_text(a, freeform) for a in aliases):
            matched_canonical.add(canon)
            continue

        missing_originals.append(original)

    score = len(matched_canonical) / max(len(jd_canonical_to_original), 1) * 100.0

    return (
        score,
        sorted(matched_canonical),
        sorted(missing_originals),
    )


# ---------------------------------------------------------------------------
# Semantic Alignment (Phase 2.3B)
# ---------------------------------------------------------------------------

_EMBEDDING_MODEL = None

def _get_embedding_model():
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer
            _EMBEDDING_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as e:
            raise RuntimeError(f"Embedding model not available: {e}")
    return _EMBEDDING_MODEL

def _get_embeddings(texts: List[str]) -> List[List[float]]:
    """Isolated for mocking in tests."""
    try:
        model = _get_embedding_model()
        embeddings = model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
    except Exception as e:
        raise RuntimeError(f"Embedding model unavailable: {e}")

def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)

def _compute_semantic_alignment(resume: StructuredResume, jd_analysis: JDAnalysis) -> float:
    jd_reqs = []
    if jd_analysis.responsibilities:
        jd_reqs.extend(jd_analysis.responsibilities)
    if jd_analysis.required_skills:
        jd_reqs.extend(jd_analysis.required_skills)
        
    jd_reqs = [r.strip() for r in jd_reqs if r and r.strip()]
    if not jd_reqs:
        return 0.0

    resume_bullets = []
    for exp in (resume.experience or []):
        if exp.bullets:
            resume_bullets.extend([b.strip() for b in exp.bullets if b and b.strip()])
    for proj in (resume.projects or []):
        if proj.description:
            resume_bullets.append(proj.description.strip())
            
    if not resume_bullets:
        return 0.0

    jd_embeddings = _get_embeddings(jd_reqs)
    resume_embeddings = _get_embeddings(resume_bullets)

    candidates = []
    for i, jd_emb in enumerate(jd_embeddings):
        for j, res_emb in enumerate(resume_embeddings):
            sim = _cosine_similarity(jd_emb, res_emb)
            if sim >= 0.45:
                candidates.append((sim, i, j))

    # Sort: similarity DESC, jd_idx ASC, resume_idx ASC
    candidates.sort(key=lambda x: (-x[0], x[1], x[2]))

    jd_matched = set()
    resume_usage = {j: 0 for j in range(len(resume_bullets))}
    total_sim = 0.0

    for sim, i, j in candidates:
        if i not in jd_matched and resume_usage[j] < 2:
            jd_matched.add(i)
            resume_usage[j] += 1
            total_sim += sim

    # Requirement-weighted average similarity (equal weights for all)
    average_sim = total_sim / len(jd_reqs)
    return average_sim * 100.0


# ---------------------------------------------------------------------------
# Quantified Impact (Phase 2.3C)
# ---------------------------------------------------------------------------

# Numbers that are almost certainly version/year references, not impact metrics.
# Pattern: 1–2 digit year-like (e.g. "v2", "2.0", "3.1"), or 4-digit years.
_NOISE_NUMBER_RE = re.compile(
    r"(?:"
    r"\bv\d+(?:\.\d+)*\b"          # version tags: v2, v3.1
    r"|\b20[0-9]{2}\b"            # calendar years 2000-2099
    r"|\b19[0-9]{2}\b"            # calendar years 1900-1999
    r")",
    re.IGNORECASE,
)

# A genuine metric: number (int/float, with optional K/M/B/% suffix or $ prefix
# or × multiplier), after stripping out noise numbers.
_METRIC_RE = re.compile(
    r"(?:"
    r"\$\s*\d[\d,]*(?:\.\d+)?(?:[KMB])?"  # $1M, $500K, $3.2B
    r"|\d[\d,]*(?:\.\d+)?%"               # 35%, 0.5%
    r"|\d[\d,]*(?:\.\d+)?[xX]"            # 2x, 10x
    r"|\d[\d,]*(?:\.\d+)?\s*[KMB]\b"     # 50K, 1M users
    r"|\b\d{2,}\b"                        # any standalone ≥2 digit number
    r")",
)

# Curated strong action verbs (first word of a bullet, whole-word, case-insensitive).
_STRONG_VERBS: FrozenSet[str] = frozenset({
    # Delivery / building
    "built", "developed", "engineered", "designed", "architected", "implemented",
    "created", "launched", "shipped", "deployed", "automated", "migrated",
    "refactored", "rewrote", "integrated", "established", "introduced",
    # Improvement
    "optimized", "improved", "reduced", "increased", "accelerated", "boosted",
    "enhanced", "streamlined", "scaled", "cut", "halved", "doubled",
    # Leadership / ownership
    "led", "owned", "managed", "coordinated", "mentored", "trained",
    "spearheaded", "championed", "directed",
    # Analysis / research
    "analysed", "analyzed", "researched", "evaluated", "identified",
    "diagnosed", "proposed",
    # Impact-centric
    "delivered", "achieved", "exceeded", "generated", "saved", "enabled",
    "eliminated", "resolved",
})

# Engineering scope phrases: team size, org-wide impact, system scope.
_SCOPE_RE = re.compile(
    r"(?:"
    r"team\s+of\s+\d+"                      # "team of 5"
    r"|\d+[\s-]+(?:person|member|engineer)s?\b"  # "5-person team"
    r"|cross[\s-]?functional"
    r"|company[\s-]?wide"
    r"|org[\s-]?wide"
    r"|enterprise[\s-]?wide"
    r"|global\b"
    r"|million\s+users?"
    r"|\d+\s*[KMB]\s*users?"
    r"|\d+\s*users?\b"
    r"|\d+\s*customers?\b"
    r"|\d+\s*clients?\b"
    r"|production\s+system"
    r"|distributed\s+system"
    r")",
    re.IGNORECASE,
)


def _bullet_has_metric(bullet: str) -> bool:
    """Return True if bullet contains at least one genuine impact metric.

    Strategy:
        1. Strip noise numbers (versions, calendar years) from a scratch copy.
        2. Search the remainder for a genuine metric pattern.

    A bullet with multiple genuine numbers still counts only once.
    """
    clean = _NOISE_NUMBER_RE.sub("", bullet)
    return bool(_METRIC_RE.search(clean))


def _bullet_has_strong_verb(bullet: str) -> bool:
    """Return True if bullet's first real word is in the strong-verb list."""
    # Strip leading punctuation/whitespace, then check first word.
    first_word_match = re.match(r"[^\w]*([\w']+)", bullet.strip(), re.IGNORECASE)
    if not first_word_match:
        return False
    return first_word_match.group(1).lower() in _STRONG_VERBS


def _experience_has_scope(exp) -> bool:  # type: ignore[type-arg]
    """Return True if any bullet in the experience entry shows engineering scope."""
    for bullet in (exp.bullets or []):
        if _SCOPE_RE.search(bullet):
            return True
    return False


def _compute_quantified_impact(resume: StructuredResume) -> float:
    """Deterministic 0–100 quantified-impact subscore.

    Three components (equal weight applied per component):
        metric_density       (40%): fraction of bullets with a genuine metric
        strong_verb_density  (30%): fraction of bullets starting with a strong verb
        scope_density        (30%): fraction of experience entries with scope evidence

    All denominators fall back to 0.0 when the relevant collection is empty.
    """
    # Collect all impact-bearing bullets from experience + projects.
    all_bullets: List[str] = []
    for exp in (resume.experience or []):
        all_bullets.extend(b.strip() for b in (exp.bullets or []) if b and b.strip())
    for proj in (resume.projects or []):
        if proj.description and proj.description.strip():
            all_bullets.append(proj.description.strip())

    n_bullets = len(all_bullets)

    # Component 1: metric density (40 points max)
    if n_bullets == 0:
        metric_score = 0.0
    else:
        metric_hits = sum(1 for b in all_bullets if _bullet_has_metric(b))
        metric_score = (metric_hits / n_bullets) * 40.0

    # Component 2: strong action-verb density (30 points max)
    if n_bullets == 0:
        verb_score = 0.0
    else:
        verb_hits = sum(1 for b in all_bullets if _bullet_has_strong_verb(b))
        verb_score = (verb_hits / n_bullets) * 30.0

    # Component 3: engineering scope evidence (30 points max)
    experiences = [e for e in (resume.experience or [])]
    n_experiences = len(experiences)
    if n_experiences == 0:
        scope_score = 0.0
    else:
        scope_hits = sum(1 for e in experiences if _experience_has_scope(e))
        scope_score = (scope_hits / n_experiences) * 30.0

    return round(metric_score + verb_score + scope_score, 2)


# ---------------------------------------------------------------------------
# Penalties (Phase 2.3D)
# ---------------------------------------------------------------------------

# How many times a canonical skill must appear across all bullets to be
# considered excessive. ≤ this threshold = legitimate repetition.
_SKILL_REPETITION_THRESHOLD = 4


def _compute_penalties(resume: StructuredResume) -> float:
    """Deterministic penalty score from 0–10 points.

    Subrules (applied independently, total capped at 10):

    Rule P1 — Excessive skill-keyword repetition (max 5 pts):
        For each canonical skill that appears more than _SKILL_REPETITION_THRESHOLD
        times across all bullets (experience + project descriptions), add 0.5 pts.
        Capped at 5 pts.  Rationale: skills used in 1–4 bullets across roles/
        projects are normal.  Only pathological saturation triggers this.
        Does NOT penalize legitimate use of a skill in different real bullets.

    Rule P2 — Duplicate/near-identical bullets (max 5 pts):
        Count bullet pairs that share a normalized form (lowercased, whitespace-
        collapsed, stripped of punctuation).  Add 1.0 pt per duplicate pair.
        Capped at 5 pts.  Rationale: copy-pasted bullets are a clear stuffing
        signal; legitimate rephrasings produce different normalized forms.

    Total = clamp(P1 + P2, 0, 10).
    """
    # Collect all bullets from experience and project descriptions.
    all_bullets: List[str] = []
    for exp in (resume.experience or []):
        all_bullets.extend(b.strip() for b in (exp.bullets or []) if b and b.strip())
    for proj in (resume.projects or []):
        if proj.description and proj.description.strip():
            all_bullets.append(proj.description.strip())

    # Extract declared skills so we only penalize actual skill repetition, not generic words.
    declared_skills: Set[str] = set()
    if resume.skills:
        for cat in [resume.skills.languages, resume.skills.frameworks,
                    resume.skills.tools, resume.skills.databases, resume.skills.concepts]:
            if cat:
                declared_skills.update(_normalize_skill(s) for s in cat)

    # --- Rule P1: canonical skill repetition ---
    # Count occurrences of each canonical skill form in all bullets combined.
    skill_counts: Dict[str, int] = {}
    for bullet in all_bullets:
        bullet_lower = bullet.lower()
        # Use the existing alias-aware normalization to get stable canonical keys.
        for token in re.findall(r"[\w#.+/-]+", bullet_lower):
            canon = _normalize_skill(token)
            skill_counts[canon] = skill_counts.get(canon, 0) + 1

    p1_raw = sum(
        0.5
        for canon, count in skill_counts.items()
        if count > _SKILL_REPETITION_THRESHOLD and canon in declared_skills
    )
    p1 = min(p1_raw, 5.0)

    # --- Rule P2: duplicate bullets ---
    def _normalize_bullet(b: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", b.lower())).strip()

    normalized_bullets = [_normalize_bullet(b) for b in all_bullets]
    seen: Dict[str, int] = {}
    duplicate_pairs = 0
    for nb in normalized_bullets:
        if nb in seen:
            seen[nb] += 1
            duplicate_pairs += 1
        else:
            seen[nb] = 1
    p2 = min(float(duplicate_pairs), 5.0)

    return round(min(p1 + p2, 10.0), 2)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def evaluate_resume(
    resume: Optional[StructuredResume],
    jd_analysis: Optional[JDAnalysis],
) -> ATSReport:
    """Deterministically evaluate a resume against a JD.

    Final weighted formula:
        final_score = clamp(0.40 * skill_match
                          + 0.40 * semantic_alignment
                          + 0.20 * quantified_impact
                          - penalties, 0, 100)

    Semantic-model failure policy:
        When the embedding model is unavailable, semantic_alignment is unknown.
        Presenting a skill-only partial score as the full weighted result would
        be misleading, so we fall back to skill_match alone as the final score
        while clearly advertising the degraded state via semantic_error.
        This is the only score consumers (frontend, graph state) receive; they
        are not given silent partial values.

    Does not mutate the resume or JD objects.
    Is independent of LangGraph, FastAPI, network, LLMs.
    """
    _empty = ATSCategoryScores(
        skill_match=0.0,
        semantic_alignment=0.0,
        quantified_impact=0.0,
        penalties=0.0,
    )
    if not resume or not jd_analysis:
        return ATSReport(
            score=0.0,
            category_scores=_empty,
            matched_skills=[],
            missing_skills=[],
        )

    skill_match, matched, missing = _compute_skill_match(resume, jd_analysis)
    quantified_impact = _compute_quantified_impact(resume)
    penalties = _compute_penalties(resume)

    semantic_error: Optional[str] = None
    semantic_available = True
    try:
        semantic_alignment = _compute_semantic_alignment(resume, jd_analysis)
    except RuntimeError as exc:
        logger.error(
            "Semantic alignment unavailable; falling back to skill-only score. "
            "Exception: %s",
            exc,
            exc_info=True,
        )
        semantic_alignment = 0.0
        semantic_error = "Model unavailable"
        semantic_available = False

    if semantic_available:
        # Full weighted formula
        raw_score = (
            0.40 * skill_match
            + 0.40 * semantic_alignment
            + 0.20 * quantified_impact
            - penalties
        )
        final_score = round(_clamp(raw_score, 0.0, 100.0), 2)
    else:
        # Degraded: only skill_match is reliable; use it directly.
        # This is a skill-only fallback, clearly flagged by semantic_error.
        final_score = round(_clamp(skill_match - penalties, 0.0, 100.0), 2)

    return ATSReport(
        score=final_score,
        is_fallback_score=not semantic_available,
        category_scores=ATSCategoryScores(
            skill_match=round(skill_match, 2),
            semantic_alignment=round(semantic_alignment, 2),
            quantified_impact=round(quantified_impact, 2),
            penalties=round(penalties, 2),
            semantic_error=semantic_error,
        ),
        matched_skills=matched,
        missing_skills=missing,
    )
