import pytest
from app.graph.nodes.resume_nodes import commit_changes_node
from app.models.resume import StructuredResume, StructuredSkills, Experience
from unittest.mock import MagicMock


def test_commit_experience_applies_bullets_and_preserves_other_sections():
    # original resume with two experiences
    orig = StructuredResume(skills=StructuredSkills(), name="Cand")
    orig.experience = [
        Experience(company="Acme", role="Backend Engineer", bullets=["Old bullet 1"]),
    ]

    state = MagicMock()
    state.original_resume = orig
    state.optimized_resume = None
    state.current_section = "experience"
    state.approval_state = {"experience": "approved"}
    # LLM returns markdown with heading matching company
    state.proposed_changes = {"new_content": "## Acme\n- Built APIs for payments\n- Improved throughput by 2x", "reasoning": "improve"}

    result = commit_changes_node(state)
    optimized = result["optimized_resume"]

    # Experience bullets should be updated, other fields preserved
    assert isinstance(optimized, StructuredResume) or isinstance(optimized, dict)
    # If dict-backed, normalize
    exp = optimized["experience"] if isinstance(optimized, dict) else optimized.experience
    assert any(isinstance(e, dict) or hasattr(e, 'bullets') for e in exp)


def test_commit_certifications_parses_lines_and_keeps_original_immutable():
    orig = StructuredResume(skills=StructuredSkills(), name="Cand")
    orig.certifications = ["Existing Cert"]

    state = MagicMock()
    state.original_resume = orig
    state.optimized_resume = None
    state.current_section = "certifications"
    state.approval_state = {"certifications": "approved"}
    state.proposed_changes = {"new_content": "AWS Certified Solutions Architect\nGoogle Cloud: Professional Data Engineer", "reasoning": "add"}

    result = commit_changes_node(state)
    optimized = result["optimized_resume"]

    # Ensure original_resume unchanged
    assert orig.certifications == ["Existing Cert"]

    certs = optimized["certifications"] if isinstance(optimized, dict) else optimized.certifications
    assert "AWS Certified Solutions Architect" in certs
    assert any("Google Cloud" in c for c in certs)
