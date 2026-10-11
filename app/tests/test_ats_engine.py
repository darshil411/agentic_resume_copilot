"""
app/tests/test_ats_engine.py
-----------------------------
Phase 2.3A — focused tests for the deterministic skill-matching engine.
Phase 2.3B — semantic alignment tests (mocked embeddings).
Phase 2.3C — quantified-impact subscore tests.

Tests are self-contained: they construct minimal StructuredResume / JDAnalysis
objects inline; no network calls, no LLMs, no model downloads.

Run with:
    pytest -q app/tests/test_ats_engine.py
"""
import pytest
from app.services.ats_engine import (
    _normalize_skill, evaluate_resume,
    _bullet_has_metric, _bullet_has_strong_verb,
    _experience_has_scope, _compute_quantified_impact,
    _compute_penalties,
)
from app.models.resume import (
    Experience,
    Project,
    StructuredResume,
    StructuredSkills,
)
from app.models.jd import JDAnalysis
from app.models.ats import ATSReport, ATSCategoryScores


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bare_skills(**kwargs) -> StructuredSkills:
    defaults = dict(languages=[], frameworks=[], tools=[], databases=[], concepts=[])
    defaults.update(kwargs)
    return StructuredSkills(**defaults)


def _minimal_resume(
    languages=None,
    frameworks=None,
    tools=None,
    databases=None,
    concepts=None,
    projects=None,
    experience=None,
) -> StructuredResume:
    return StructuredResume(
        name="Test Candidate",
        skills=StructuredSkills(
            languages=languages or [],
            frameworks=frameworks or [],
            tools=tools or [],
            databases=databases or [],
            concepts=concepts or [],
        ),
        projects=projects or [],
        experience=experience or [],
    )


def _minimal_jd(*skills: str) -> JDAnalysis:
    return JDAnalysis(
        role_summary="Test role",
        required_skills=list(skills),
        responsibilities=[],
        keywords=[],
        tools=[],
        experience_requirements="",
    )


# ===========================================================================
# 1. Normalization
# ===========================================================================

class TestNormalization:
    """_normalize_skill must map raw spellings to canonical forms."""

    def test_postgresql_canonical(self):
        assert _normalize_skill("PostgreSQL") == "postgresql"

    def test_postgres_to_postgresql(self):
        assert _normalize_skill("Postgres") == "postgresql"

    def test_pg_to_postgresql(self):
        assert _normalize_skill("pg") == "postgresql"

    def test_react_canonical(self):
        assert _normalize_skill("React") == "react"

    def test_reactjs_to_react(self):
        assert _normalize_skill("React.js") == "react"

    def test_reactjs_nospace_to_react(self):
        assert _normalize_skill("ReactJS") == "react"

    def test_rest_api_canonical(self):
        assert _normalize_skill("REST API") == "rest_api"

    def test_restful_api_to_restapi(self):
        assert _normalize_skill("RESTful API") == "rest_api"

    def test_sklearn_to_scikit_learn(self):
        assert _normalize_skill("sklearn") == "scikit_learn"

    def test_scikit_learn_hyphen(self):
        assert _normalize_skill("scikit-learn") == "scikit_learn"

    def test_aws_lowercase(self):
        assert _normalize_skill("AWS") == "aws"

    def test_amazon_web_services_to_aws(self):
        assert _normalize_skill("Amazon Web Services") == "aws"

    def test_k8s_to_kubernetes(self):
        assert _normalize_skill("K8s") == "kubernetes"

    def test_kubernetes_canonical(self):
        assert _normalize_skill("Kubernetes") == "kubernetes"

    def test_nodejs_canonical(self):
        assert _normalize_skill("Node.js") == "nodejs"

    def test_node_to_nodejs(self):
        assert _normalize_skill("Node") == "nodejs"

    def test_nodejs_nospace(self):
        assert _normalize_skill("NodeJS") == "nodejs"


# ===========================================================================
# 2. False positives — must NOT match
# ===========================================================================

class TestFalsePositives:
    """Boundary-safe matching must reject substring / prefix coincidences."""

    def test_c_does_not_match_css(self):
        resume = _minimal_resume(languages=["CSS"])
        jd = _minimal_jd("C")
        report = evaluate_resume(resume, jd)
        assert "c" not in report.matched_skills, (
            "Skill 'C' must not match 'CSS'"
        )

    def test_react_does_not_match_reaction(self):
        """'React' in JD must not be satisfied by 'Reaction' in resume text."""
        resume = _minimal_resume(
            experience=[Experience(
                company="Lab",
                role="Engineer",
                bullets=["Studied Reaction kinetics"],
            )]
        )
        jd = _minimal_jd("React")
        report = evaluate_resume(resume, jd)
        assert "react" not in report.matched_skills, (
            "Skill 'React' must not match the word 'Reaction'"
        )

    def test_go_does_not_match_google(self):
        """'Go' in JD must not be satisfied by 'Google Cloud' in resume."""
        resume = _minimal_resume(
            experience=[Experience(
                company="Corp",
                role="SRE",
                bullets=["Deployed on Google Cloud Platform"],
            )]
        )
        jd = _minimal_jd("Go")
        report = evaluate_resume(resume, jd)
        # canonical of "Go" is "nodejs"? No — "go" has no alias; canonical = "go"
        assert "go" not in report.matched_skills, (
            "Skill 'Go' must not match 'Google Cloud'"
        )


# ===========================================================================
# 3. Positive evidence — structured sections
# ===========================================================================

class TestPositiveEvidence:
    def test_skill_in_explicit_skills(self):
        resume = _minimal_resume(frameworks=["FastAPI"])
        jd = _minimal_jd("FastAPI")
        report = evaluate_resume(resume, jd)
        assert "fastapi" in report.matched_skills

    def test_skill_in_project_tech_stack(self):
        resume = _minimal_resume(
            projects=[Project(
                title="My App",
                description="An AI service",
                tech_stack=["LangGraph"],
            )]
        )
        jd = _minimal_jd("LangGraph")
        report = evaluate_resume(resume, jd)
        assert "langgraph" in report.matched_skills

    def test_skill_in_project_description(self):
        """FastAPI mentioned in a project description must be matched."""
        resume = _minimal_resume(
            projects=[Project(
                title="Backend Service",
                description="Built a FastAPI backend with async endpoints",
                tech_stack=[],
            )]
        )
        jd = _minimal_jd("FastAPI")
        report = evaluate_resume(resume, jd)
        assert "fastapi" in report.matched_skills

    def test_skill_in_experience_bullet(self):
        """PostgreSQL mentioned in an experience bullet must be matched."""
        resume = _minimal_resume(
            experience=[Experience(
                company="Startup",
                role="Backend Engineer",
                bullets=["Designed PostgreSQL database schema for analytics"],
            )]
        )
        jd = _minimal_jd("PostgreSQL")
        report = evaluate_resume(resume, jd)
        assert "postgresql" in report.matched_skills


# ===========================================================================
# 4. Alias evidence — aliases across sections
# ===========================================================================

class TestAliasEvidence:
    """Alias pairs must match regardless of which spelling appears where."""

    def test_jd_reactjs_resume_react_in_skills(self):
        resume = _minimal_resume(frameworks=["React"])
        jd = _minimal_jd("React.js")
        report = evaluate_resume(resume, jd)
        assert "react" in report.matched_skills

    def test_jd_postgresql_resume_postgres_in_bullet(self):
        resume = _minimal_resume(
            experience=[Experience(
                company="Co",
                role="DBA",
                bullets=["Optimized Postgres queries"],
            )]
        )
        jd = _minimal_jd("PostgreSQL")
        report = evaluate_resume(resume, jd)
        assert "postgresql" in report.matched_skills

    def test_jd_kubernetes_resume_k8s_in_tech_stack(self):
        resume = _minimal_resume(
            projects=[Project(
                title="Platform",
                description="Infra project",
                tech_stack=["K8s"],
            )]
        )
        jd = _minimal_jd("Kubernetes")
        report = evaluate_resume(resume, jd)
        assert "kubernetes" in report.matched_skills

    def test_jd_rest_api_resume_restful_in_bullet(self):
        resume = _minimal_resume(
            experience=[Experience(
                company="Co",
                role="Dev",
                bullets=["Designed RESTful API endpoints"],
            )]
        )
        jd = _minimal_jd("REST API")
        report = evaluate_resume(resume, jd)
        assert "rest_api" in report.matched_skills

    def test_jd_nodejs_resume_node_in_skills(self):
        resume = _minimal_resume(tools=["Node"])
        jd = _minimal_jd("Node.js")
        report = evaluate_resume(resume, jd)
        assert "nodejs" in report.matched_skills


# ===========================================================================
# 5. Multi-word skills — phrase-level matching
# ===========================================================================

class TestMultiWordSkills:
    def test_machine_learning_in_bullet(self):
        resume = _minimal_resume(
            experience=[Experience(
                company="AI Corp",
                role="Engineer",
                bullets=["Built a machine learning pipeline for NLP tasks"],
            )]
        )
        jd = _minimal_jd("Machine Learning")
        report = evaluate_resume(resume, jd)
        assert "machine_learning" in report.matched_skills

    def test_machine_learning_not_matched_by_individual_words(self):
        """'machine' alone or 'learning' alone must not satisfy 'Machine Learning'."""
        # The resume has "machine" and "learning" as separate, unrelated skills
        resume = _minimal_resume(
            experience=[Experience(
                company="Factory",
                role="Operator",
                bullets=["Operated industrial machine", "E-learning platform user"],
            )]
        )
        jd = _minimal_jd("Machine Learning")
        report = evaluate_resume(resume, jd)
        # The phrase "machine learning" does not appear contiguously → no match
        assert "machine_learning" not in report.matched_skills


# ===========================================================================
# 6. Skill match score
# ===========================================================================

class TestSkillMatchScore:
    def test_two_of_three_skills(self):
        """2 of 3 JD skills matched → skill_match ≈ 66.6667."""
        resume = _minimal_resume(
            languages=["Python"],
            frameworks=["FastAPI"],
        )
        jd = _minimal_jd("Python", "FastAPI", "PostgreSQL")
        report = evaluate_resume(resume, jd)
        expected = 2 / 3 * 100
        assert abs(report.category_scores.skill_match - expected) < 0.01

    def test_all_skills_matched(self):
        resume = _minimal_resume(
            languages=["Python"],
            frameworks=["FastAPI"],
            databases=["PostgreSQL"],
        )
        jd = _minimal_jd("Python", "FastAPI", "PostgreSQL")
        report = evaluate_resume(resume, jd)
        assert report.category_scores.skill_match == 100.0

    def test_no_skills_matched(self):
        resume = _minimal_resume(languages=["Ruby"])
        jd = _minimal_jd("Python", "FastAPI")
        report = evaluate_resume(resume, jd)
        assert report.category_scores.skill_match == 0.0
        assert report.score == 0.0

    def test_empty_jd_skills(self):
        """No required skills → score 0, no matched, no missing."""
        resume = _minimal_resume(languages=["Python"])
        jd = _minimal_jd()  # empty required_skills
        report = evaluate_resume(resume, jd)
        assert report.score == 0.0
        assert report.matched_skills == []
        assert report.missing_skills == []

    def test_missing_skills_uses_original_jd_name(self):
        """missing_skills should carry the original JD string, not the canonical."""
        resume = _minimal_resume(languages=["Python"])
        jd = _minimal_jd("Python", "Node.js", "PostgreSQL")
        report = evaluate_resume(resume, jd)
        # "Node.js" and "PostgreSQL" are missing; their original strings must appear
        missing_lower = [s.lower() for s in report.missing_skills]
        assert any("node" in m for m in missing_lower), (
            "Original JD name for Node.js must appear in missing_skills"
        )
        assert any("postgres" in m.lower() for m in report.missing_skills)


# ===========================================================================
# 7. Determinism
# ===========================================================================

class TestDeterminism:
    def test_same_input_produces_identical_output(self):
        resume = _minimal_resume(
            languages=["Python"],
            frameworks=["FastAPI", "React"],
            databases=["PostgreSQL"],
            projects=[Project(
                title="API Service",
                description="Built a RESTful API with FastAPI",
                tech_stack=["Docker"],
            )],
            experience=[Experience(
                company="Corp",
                role="Engineer",
                bullets=["Used machine learning pipelines"],
            )],
        )
        jd = _minimal_jd("Python", "FastAPI", "PostgreSQL", "Docker", "React")

        report_a = evaluate_resume(resume, jd)
        report_b = evaluate_resume(resume, jd)

        assert report_a.score == report_b.score
        assert report_a.matched_skills == report_b.matched_skills
        assert report_a.missing_skills == report_b.missing_skills
        assert report_a.category_scores.skill_match == report_b.category_scores.skill_match


# ===========================================================================
# 8. Null / guard cases
# ===========================================================================

class TestNullGuards:
    def test_none_resume_returns_zero_report(self):
        jd = _minimal_jd("Python")
        report = evaluate_resume(None, jd)  # type: ignore[arg-type]
        assert report.score == 0.0
        assert report.matched_skills == []
        assert report.missing_skills == []

    def test_none_jd_returns_zero_report(self):
        resume = _minimal_resume(languages=["Python"])
        report = evaluate_resume(resume, None)  # type: ignore[arg-type]
        assert report.score == 0.0

    def test_report_has_new_category_fields(self):
        """ATSReport must expose skill_match / semantic_alignment / quantified_impact."""
        resume = _minimal_resume(languages=["Python"])
        jd = _minimal_jd("Python")
        report = evaluate_resume(resume, jd)
        assert hasattr(report.category_scores, "skill_match")
        assert hasattr(report.category_scores, "semantic_alignment")
        assert hasattr(report.category_scores, "quantified_impact")
        assert hasattr(report.category_scores, "penalties")

    def test_placeholder_fields_are_zero(self):
        """penalties must be 0.0 for a minimal resume with no stuffing."""
        resume = _minimal_resume(languages=["Python"])
        jd = _minimal_jd("Python")
        report = evaluate_resume(resume, jd)
        # quantified_impact may be non-zero (Phase 2.3C implemented)
        assert report.category_scores.penalties == 0.0


# ===========================================================================
# 9. Semantic Alignment (Phase 2.3B)
# ===========================================================================

import pytest
from unittest.mock import patch

class TestSemanticAlignment:
    @pytest.fixture(autouse=True)
    def mock_embeddings(self):
        """Mock _get_embeddings to return deterministic predictable vectors."""
        def mock_get_embeddings(texts):
            res = []
            for t in texts:
                t = t.lower()
                # Simple orthogonal vectors based on content
                if "backend" in t:
                    res.append([1.0, 0.0, 0.0, 0.0])
                elif "frontend" in t:
                    res.append([0.0, 1.0, 0.0, 0.0])
                elif "database" in t:
                    res.append([0.0, 0.0, 1.0, 0.0])
                elif "cloud" in t:
                    res.append([0.0, 0.0, 0.0, 1.0])
                elif "fullstack" in t:
                    # Matches backend and frontend equally, similarity ~ 0.707
                    res.append([0.707, 0.707, 0.0, 0.0])
                elif "weak match" in t:
                    # Similarity < 0.45 threshold against backend
                    res.append([0.4, 0.0, 0.9, 0.0])
                else:
                    res.append([0.0, 0.0, 0.0, 0.0])
            return res

        with patch("app.services.ats_engine._get_embeddings", side_effect=mock_get_embeddings):
            yield

    def test_greedy_assignment_and_threshold(self):
        """Test threshold 0.45 and greedy match."""
        jd = JDAnalysis(
            role_summary="", keywords=[], tools=[],
            required_skills=[],
            responsibilities=["backend development", "cloud deployment", "something else"]
        )
        resume = _minimal_resume(
            experience=[Experience(
                company="Corp",
                role="Engineer",
                bullets=["I did backend stuff", "weak match here"]
            )]
        )
        report = evaluate_resume(resume, jd)
        assert pytest.approx(report.category_scores.semantic_alignment, 0.1) == 33.33

    def test_tie_breaking(self):
        """Test sorting by jd_idx ASC and resume_idx ASC."""
        jd = JDAnalysis(
            role_summary="", keywords=[], tools=[],
            required_skills=[],
            responsibilities=["backend 1", "backend 2"]
        )
        resume = _minimal_resume(
            experience=[Experience(
                company="Corp",
                role="Engineer",
                bullets=["backend A", "backend B"]
            )]
        )
        report = evaluate_resume(resume, jd)
        assert report.category_scores.semantic_alignment == 100.0

    def test_reuse_cap(self):
        """Test that a resume bullet is used at most twice."""
        jd = JDAnalysis(
            role_summary="", keywords=[], tools=[],
            required_skills=[],
            responsibilities=["backend 1", "backend 2", "backend 3"]
        )
        resume = _minimal_resume(
            experience=[Experience(
                company="Corp",
                role="Engineer",
                bullets=["backend A"]
            )]
        )
        report = evaluate_resume(resume, jd)
        assert pytest.approx(report.category_scores.semantic_alignment, 0.1) == 66.67

    def test_unmatched_requirements(self):
        """Unmatched requirements score 0 and drag down the average."""
        jd = JDAnalysis(
            role_summary="", keywords=[], tools=[],
            required_skills=[],
            responsibilities=["backend"]
        )
        resume = _minimal_resume(
            experience=[Experience(
                company="Corp",
                role="Engineer",
                bullets=["frontend"]
            )]
        )
        report = evaluate_resume(resume, jd)
        assert report.category_scores.semantic_alignment == 0.0

    def test_determinism_and_no_requirements(self):
        """Empty requirements should yield 0.0 semantic alignment."""
        jd = JDAnalysis(
            role_summary="", keywords=[], tools=[],
            required_skills=[],
            responsibilities=[]
        )
        resume = _minimal_resume(
            experience=[Experience(
                company="Corp",
                role="Engineer",
                bullets=["backend"]
            )]
        )
        report = evaluate_resume(resume, jd)
        assert report.category_scores.semantic_alignment == 0.0

    def test_model_unavailable_preserves_skill_match(self):
        """Model load failure should set semantic_error and preserve skill_match."""
        jd = JDAnalysis(
            role_summary="", keywords=[], tools=[],
            required_skills=["Python"],
            responsibilities=["backend development"]
        )
        resume = _minimal_resume(
            languages=["Python"],
            experience=[Experience(
                company="Corp",
                role="Engineer",
                bullets=["I did backend stuff"]
            )]
        )
        with patch("app.services.ats_engine._get_embeddings", side_effect=RuntimeError("Unavailable")):
            report = evaluate_resume(resume, jd)
            
        assert report.score == 100.0  # Skill match is 1 of 1 -> 100%
        assert report.category_scores.skill_match == 100.0
        assert report.category_scores.semantic_alignment == 0.0
        assert report.category_scores.semantic_error == "Model unavailable"


# ===========================================================================
# 10. Quantified Impact (Phase 2.3C)
# ===========================================================================

class TestBulletHasMetric:
    """Unit tests for _bullet_has_metric."""

    def test_percentage_counts_as_metric(self):
        assert _bullet_has_metric("Reduced latency by 35%") is True

    def test_dollar_amount_counts_as_metric(self):
        assert _bullet_has_metric("Generated $1.2M in revenue") is True

    def test_multiplier_counts_as_metric(self):
        assert _bullet_has_metric("Improved throughput by 3x") is True

    def test_large_plain_number_counts_as_metric(self):
        assert _bullet_has_metric("Served 50,000 requests per second") is True

    def test_two_digit_number_counts_as_metric(self):
        assert _bullet_has_metric("Led a team of 12 engineers") is True

    def test_multiple_numbers_count_only_once(self):
        # The bullet has 35% AND 12; should still return True (not double-count)
        assert _bullet_has_metric("Reduced latency by 35% across 12 services") is True

    def test_version_number_does_not_count(self):
        assert _bullet_has_metric("Upgraded to Python v3.11") is False

    def test_calendar_year_does_not_count(self):
        assert _bullet_has_metric("Joined the company in 2022") is False

    def test_single_digit_number_does_not_count(self):
        # Single standalone digits are too ambiguous to be impact metrics
        assert _bullet_has_metric("Stage 1 of the pipeline") is False

    def test_no_numbers_returns_false(self):
        assert _bullet_has_metric("Developed a microservices architecture") is False

    def test_k_suffix_counts_as_metric(self):
        assert _bullet_has_metric("Handled 500K daily active users") is True


class TestBulletHasStrongVerb:
    """Unit tests for _bullet_has_strong_verb."""

    def test_built_is_strong_verb(self):
        assert _bullet_has_strong_verb("Built a distributed caching layer") is True

    def test_reduced_is_strong_verb(self):
        assert _bullet_has_strong_verb("Reduced deployment time by 40%") is True

    def test_led_is_strong_verb(self):
        assert _bullet_has_strong_verb("Led a cross-functional team of 8") is True

    def test_weak_verb_returns_false(self):
        assert _bullet_has_strong_verb("Worked on backend features") is False

    def test_responsibility_verb_returns_false(self):
        assert _bullet_has_strong_verb("Participated in code reviews") is False

    def test_verb_matching_is_case_insensitive(self):
        assert _bullet_has_strong_verb("OPTIMIZED the database queries") is True

    def test_empty_bullet_returns_false(self):
        assert _bullet_has_strong_verb("") is False

    def test_bullet_starting_with_dash_strips_correctly(self):
        # Leading punctuation should be ignored, verb extracted from first word
        assert _bullet_has_strong_verb("- Deployed the service to production") is True


class TestExperienceHasScope:
    """Unit tests for _experience_has_scope."""

    def test_team_of_n_counts_as_scope(self):
        exp = Experience(company="X", role="Lead", bullets=["Led team of 5 engineers"])
        assert _experience_has_scope(exp) is True

    def test_cross_functional_counts_as_scope(self):
        exp = Experience(company="X", role="Lead", bullets=["Coordinated cross-functional effort"])
        assert _experience_has_scope(exp) is True

    def test_company_wide_counts_as_scope(self):
        exp = Experience(company="X", role="Eng", bullets=["Rolled out company-wide monitoring"])
        assert _experience_has_scope(exp) is True

    def test_users_count_counts_as_scope(self):
        exp = Experience(company="X", role="Eng", bullets=["Served 50000 users globally"])
        assert _experience_has_scope(exp) is True

    def test_no_scope_evidence_returns_false(self):
        exp = Experience(company="X", role="Eng", bullets=["Fixed a bug in the login flow"])
        assert _experience_has_scope(exp) is False

    def test_empty_bullets_returns_false(self):
        exp = Experience(company="X", role="Eng", bullets=[])
        assert _experience_has_scope(exp) is False


class TestComputeQuantifiedImpact:
    """Integration tests for _compute_quantified_impact."""

    def test_empty_resume_returns_zero(self):
        resume = _minimal_resume()
        assert _compute_quantified_impact(resume) == 0.0

    def test_all_quantified_bullets_high_metric_score(self):
        """4/4 metric bullets → full 40 metric points."""
        resume = _minimal_resume(
            experience=[Experience(
                company="Corp", role="Eng",
                bullets=[
                    "Reduced latency by 40%",
                    "Increased revenue by $2M",
                    "Served 100K users daily",
                    "Achieved 99.99% uptime",
                ]
            )]
        )
        score = _compute_quantified_impact(resume)
        assert score >= 40.0

    def test_no_metric_bullets_zero_metric_component(self):
        """Bullets with no metrics should contribute 0 to metric component."""
        resume = _minimal_resume(
            experience=[Experience(
                company="Corp", role="Eng",
                bullets=[
                    "Worked on backend features",
                    "Participated in code reviews",
                ]
            )]
        )
        score = _compute_quantified_impact(resume)
        assert score < 40.0  # metric component must be 0

    def test_multiple_numbers_in_one_bullet_counted_once(self):
        """A bullet with 3 numbers (35%, 12 services, 50ms) counts only once for metric density."""
        resume = _minimal_resume(
            experience=[Experience(
                company="Corp", role="Eng",
                bullets=[
                    "Reduced latency by 35% across 12 services, from 200ms to 50ms",
                    "No metrics here",
                ]
            )]
        )
        score = _compute_quantified_impact(resume)
        # 1 of 2 bullets has metrics  → metric_score = (1/2) * 40 = 20.0
        # "Reduced" is a strong verb, "No metrics" is not → verb_score = (1/2) * 30 = 15.0
        # 0 of 1 experience has scope  → scope_score = 0
        # Total = 35.0
        assert pytest.approx(score, abs=0.1) == 35.0

    def test_strong_verb_density_contributes(self):
        """All strong-verb bullets should add up to ~30 verb points."""
        resume = _minimal_resume(
            experience=[Experience(
                company="Corp", role="Eng",
                bullets=[
                    "Built the API gateway",
                    "Deployed to AWS",
                    "Optimized the query planner",
                ]
            )]
        )
        score = _compute_quantified_impact(resume)
        # 3/3 strong verbs → verb_score = 30
        assert score >= 30.0

    def test_scope_evidence_contributes(self):
        """Scope evidence in a single experience entry awards full 30 scope points."""
        resume = _minimal_resume(
            experience=[Experience(
                company="Corp", role="Eng",
                bullets=["Led cross-functional team of 8 engineers"]
            )]
        )
        score = _compute_quantified_impact(resume)
        # 1/1 experience has scope → scope_score = 30
        assert score >= 30.0

    def test_score_bounded_between_0_and_100(self):
        """Perfect resume must not exceed 100."""
        resume = _minimal_resume(
            experience=[Experience(
                company="Corp", role="Eng",
                bullets=[
                    "Reduced latency by 40% across team of 10",
                    "Built $2M revenue pipeline, serving 500K users globally",
                    "Optimized distributed system 3x, company-wide rollout",
                ]
            )]
        )
        score = _compute_quantified_impact(resume)
        assert 0.0 <= score <= 100.0

    def test_version_numbers_not_counted_as_metrics(self):
        """Version numbers like v3.11 or 2024 must not trigger metric detection."""
        resume = _minimal_resume(
            experience=[Experience(
                company="Corp", role="Eng",
                bullets=[
                    "Migrated to Python v3.11 in 2023",
                    "Upgraded React to v18",
                ]
            )]
        )
        score = _compute_quantified_impact(resume)
        # No genuine metrics → metric_score = 0
        # "Migrated" is a strong verb; "Upgraded" is not in our list → verb_score = 0.5 * 30 = 15
        assert score < 20.0  # only partial verb credit, no metric or scope

    def test_skill_match_score_unchanged_by_quantified_impact(self):
        """Final score is the weighted formula, not just skill_match."""
        jd = JDAnalysis(role_summary="", keywords=[], tools=[], required_skills=["Python"], responsibilities=[])
        resume = _minimal_resume(
            languages=["Python"],
            experience=[Experience(
                company="Corp", role="Eng",
                bullets=["Reduced latency by 40%, serving 100K users"]
            )]
        )
        report = evaluate_resume(resume, jd)
        # skill_match=100, quantified_impact>0 — score is now the weighted formula
        assert report.category_scores.quantified_impact > 0.0  # non-zero
        # score must be within valid range and have all category fields
        assert 0.0 <= report.score <= 100.0
        assert hasattr(report.category_scores, "skill_match")
        assert hasattr(report.category_scores, "semantic_alignment")
        assert hasattr(report.category_scores, "penalties")

    def test_determinism_same_input_same_output(self):
        """Calling twice on same resume returns identical quantified_impact."""
        resume = _minimal_resume(
            experience=[Experience(
                company="Corp", role="Eng",
                bullets=["Built a 3x faster caching layer for 50K users"]
            )]
        )
        assert _compute_quantified_impact(resume) == _compute_quantified_impact(resume)

    def test_project_description_included_as_bullet(self):
        """Project descriptions are counted as evidence bullets."""
        resume = _minimal_resume(
            projects=[Project(
                title="Cache System",
                description="Reduced cache misses by 60% serving 200K users",
                tech_stack=[]
            )]
        )
        score = _compute_quantified_impact(resume)
        assert score > 0.0


# ===========================================================================
# 11. Penalties (Phase 2.3D)
# ===========================================================================

class TestPenalties:
    """Unit tests for _compute_penalties."""

    def test_empty_resume_zero_penalty(self):
        resume = _minimal_resume()
        assert _compute_penalties(resume) == 0.0

    def test_no_repetition_zero_penalty(self):
        """Normal resume with distinct bullets has no penalty."""
        resume = _minimal_resume(
            experience=[Experience(company="X", role="Eng", bullets=[
                "Built a REST API in Python",
                "Deployed the service with Docker",
                "Optimized PostgreSQL queries",
            ])]
        )
        assert _compute_penalties(resume) == 0.0

    def test_legitimate_technical_repetition_no_penalty(self):
        """A skill appearing in 4 bullets across roles must not be penalized."""
        # Python appears exactly 4 times — at the threshold, not above it.
        bullets = [
            "Built microservices in Python",
            "Wrote unit tests in Python",
            "Deployed Python lambdas to AWS",
            "Used Python for data processing",
        ]
        resume = _minimal_resume(
            languages=["Python"],
            experience=[Experience(company="X", role="Eng", bullets=bullets)]
        )
        assert _compute_penalties(resume) == 0.0

    def test_excessive_skill_repetition_triggers_p1(self):
        """A skill appearing >4 times should trigger penalty P1."""
        bullets = [
            "Built service in Python",
            "Optimized Python code",
            "Tested Python modules",
            "Reviewed Python PRs",
            "Deployed Python packages",  # 5th occurrence: above threshold
        ]
        resume = _minimal_resume(
            languages=["Python"],
            experience=[Experience(company="X", role="Eng", bullets=bullets)]
        )
        penalty = _compute_penalties(resume)
        assert penalty > 0.0

    def test_excessive_generic_word_no_p1_penalty(self):
        """A non-skill word appearing >4 times should NOT trigger penalty P1."""
        bullets = [
            "Built a system",
            "Optimized the system",
            "Tested the system",
            "Reviewed the system",
            "Deployed the system",  # 5th occurrence of 'system'
        ]
        resume = _minimal_resume(
            languages=["Python"],  # 'system' is not declared
            experience=[Experience(company="X", role="Eng", bullets=bullets)]
        )
        penalty = _compute_penalties(resume)
        assert penalty == 0.0

    def test_duplicate_bullets_trigger_p2(self):
        """Exact duplicate bullets should trigger penalty P2."""
        bullet = "Built a REST API service"
        resume = _minimal_resume(
            experience=[Experience(company="X", role="Eng", bullets=[bullet, bullet])]
        )
        penalty = _compute_penalties(resume)
        assert penalty >= 1.0  # at least 1 duplicate pair

    def test_near_identical_bullets_trigger_p2(self):
        """Bullets that differ only in punctuation should be treated as duplicates."""
        resume = _minimal_resume(
            experience=[Experience(company="X", role="Eng", bullets=[
                "Built a REST API.",
                "Built a REST API",  # identical after normalization
            ])]
        )
        penalty = _compute_penalties(resume)
        assert penalty >= 1.0

    def test_penalty_capped_at_10(self):
        """Total penalty must never exceed 10."""
        # Massive repetition of same bullet = maximum P2
        bullet = "Used Python to build Python-based Python pipelines"
        resume = _minimal_resume(
            experience=[Experience(company="X", role="Eng",
                                   bullets=[bullet] * 20)]
        )
        penalty = _compute_penalties(resume)
        assert penalty <= 10.0

    def test_penalty_within_bounds(self):
        """Any resume must produce a penalty in [0, 10]."""
        resume = _minimal_resume(
            experience=[Experience(company="X", role="Eng", bullets=[
                "Built a Python service",
                "Built a Python service",
                "Built a Python service",
            ])]
        )
        p = _compute_penalties(resume)
        assert 0.0 <= p <= 10.0


# ===========================================================================
# 12. Final weighted formula
# ===========================================================================

class TestFinalFormula:
    """Tests for the weighted score formula in evaluate_resume."""

    @pytest.fixture(autouse=True)
    def patch_semantic(self):
        """Patch _compute_semantic_alignment to return a known value."""
        import app.services.ats_engine as eng
        original = eng._compute_semantic_alignment
        eng._compute_semantic_alignment = lambda r, j: 80.0
        yield
        eng._compute_semantic_alignment = original

    def test_weighted_formula_known_components(self):
        """With known component values verify the weighted formula."""
        # skill_match = 100 (Python matched 1/1)
        # semantic_alignment = 80 (mocked)
        # quantified_impact: resume has strong verb + metric -> >0
        # penalties = 0 (no repetition)
        # Expected: 0.4*100 + 0.4*80 + 0.2*qi - 0 = 40 + 32 + 0.2*qi
        jd = _minimal_jd("Python")
        resume = _minimal_resume(
            languages=["Python"],
            experience=[Experience(company="X", role="Eng",
                                   bullets=["Built an API"])]
        )
        report = evaluate_resume(resume, jd)
        qi = report.category_scores.quantified_impact
        expected = round(0.4 * 100 + 0.4 * 80 + 0.2 * qi, 2)
        assert report.score == expected
        assert report.is_fallback_score is False

    def test_score_clamped_at_100(self):
        """Score must never exceed 100 even with perfect components."""
        import app.services.ats_engine as eng
        original = eng._compute_semantic_alignment
        eng._compute_semantic_alignment = lambda r, j: 100.0
        try:
            jd = _minimal_jd("Python")
            resume = _minimal_resume(languages=["Python"])
            report = evaluate_resume(resume, jd)
            assert report.score <= 100.0
        finally:
            eng._compute_semantic_alignment = original

    def test_score_clamped_at_zero(self):
        """Score must never fall below 0 even with maximum penalties."""
        import app.services.ats_engine as eng
        orig_sem = eng._compute_semantic_alignment
        orig_pen = eng._compute_penalties
        eng._compute_semantic_alignment = lambda r, j: 0.0
        eng._compute_penalties = lambda r: 10.0  # force maximum penalty
        try:
            jd = _minimal_jd("Python")
            resume = _minimal_resume(languages=["Python"])
            report = evaluate_resume(resume, jd)
            assert report.score >= 0.0
        finally:
            eng._compute_semantic_alignment = orig_sem
            eng._compute_penalties = orig_pen

    def test_penalties_reduce_final_score(self):
        """A resume with duplicate bullets has a lower score than one without."""
        jd = _minimal_jd("Python")
        clean_resume = _minimal_resume(
            languages=["Python"],
            experience=[Experience(company="X", role="Eng",
                                   bullets=["Built a Python API"])]
        )
        stuffed_resume = _minimal_resume(
            languages=["Python"],
            experience=[Experience(company="X", role="Eng", bullets=[
                "Built a Python API",
                "Built a Python API",  # duplicate
            ])]
        )
        clean_report = evaluate_resume(clean_resume, jd)
        stuffed_report = evaluate_resume(stuffed_resume, jd)
        assert stuffed_report.score <= clean_report.score

    def test_semantic_unavailable_uses_skill_fallback(self):
        """When semantic model fails, score is skill_match minus penalties (not weighted)."""
        import app.services.ats_engine as eng
        
        # Override the autouse fixture's mock with our own error-raising mock
        orig = eng._compute_semantic_alignment
        def _raise_err(r, j):
            raise RuntimeError("Unavailable")
        eng._compute_semantic_alignment = _raise_err
        
        try:
            jd = _minimal_jd("Python")
            resume = _minimal_resume(
                languages=["Python"],
                experience=[Experience(company="X", role="Eng",
                                       bullets=["Built a Python API"])]
            )
            report = evaluate_resume(resume, jd)
        finally:
            eng._compute_semantic_alignment = orig

        assert report.category_scores.semantic_error == "Model unavailable"
        assert report.category_scores.semantic_alignment == 0.0
        # score = skill_match - penalties, clamped; with no stuffing: = 100.0
        expected = round(max(0.0, report.category_scores.skill_match
                             - report.category_scores.penalties), 2)
        assert report.score == expected
        assert report.is_fallback_score is True

    def test_matched_missing_skills_preserved(self):
        """matched_skills and missing_skills must be present after formula integration."""
        jd = _minimal_jd("Python", "Docker")
        resume = _minimal_resume(languages=["Python"])
        report = evaluate_resume(resume, jd)
        assert "python" in report.matched_skills
        assert any("docker" in s.lower() for s in report.missing_skills)

    def test_report_serialises_cleanly(self):
        """ATSReport must serialise to JSON without error and include key fields."""
        import json
        jd = _minimal_jd("Python")
        resume = _minimal_resume(languages=["Python"])
        report = evaluate_resume(resume, jd)
        data = json.loads(report.model_dump_json())
        assert "score" in data
        assert "category_scores" in data
        assert "matched_skills" in data
        assert "missing_skills" in data
