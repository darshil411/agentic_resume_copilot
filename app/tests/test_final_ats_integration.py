import pytest
from app.graph.nodes.resume_nodes import commit_changes_node
from app.graph.nodes.foundation_nodes import final_ats_node
from app.models.resume import StructuredResume, StructuredSkills
from app.models.jd import JDAnalysis
from app.graph.state.global_state import GlobalGraphState
from unittest.mock import MagicMock, patch

def test_commit_changes_skills_dict_representation():
    """Verify commit_changes_node handles dict optimized_resume properly."""
    
    # Simulate the resume as a dict, as it might be loaded from SQLite checkpoint
def test_commit_changes_skills_dict_representation():
    """Verify commit_changes_node handles dict optimized_resume properly."""
    
    optimized_resume = {
        "name": "Candidate",
        "skills": {
            "languages": ["Python"],
            "frameworks": ["FastAPI"],
            "tools": [],
            "databases": [],
            "concepts": []
        }
    }
    
    state = MagicMock()
    state.original_resume = StructuredResume(skills=StructuredSkills())
    state.optimized_resume = optimized_resume
    state.current_section = "skills"
    state.approval_state = {"skills": "approved"}
    state.proposed_changes = {"new_content": "Languages: Go, Rust\nFrameworks: Django", "reasoning": "better"}
    
    result = commit_changes_node(state)
    opt = result["optimized_resume"]
    
    assert isinstance(opt, dict)
    assert isinstance(opt["skills"], dict)
    assert "Go" in opt["skills"]["languages"]
    assert "Django" in opt["skills"]["frameworks"]


def test_final_ats_node_with_dict_state():
    """Verify final_ats_node safely parses dict resumes and JDs into models."""
    
    optimized_resume = {
        "name": "Candidate",
        "skills": {
            "languages": ["Python", "Go"],
            "frameworks": ["FastAPI"],
            "tools": [],
            "databases": [],
            "concepts": []
        }
    }
    jd_analysis = {
        "role_summary": "Role",
        "required_skills": ["Python", "Docker"],
        "responsibilities": [],
        "keywords": [],
        "tools": [],
        "experience_requirements": ""
    }
    
    state = MagicMock()
    state.optimized_resume = optimized_resume
    state.jd_analysis = jd_analysis
    state.current_section = "DONE"
    
    with patch("app.services.ats_engine._get_embeddings", return_value=[[0.1]*384]):
        result = final_ats_node(state)
    
    assert "optimized_ats_report" in result
    report = result["optimized_ats_report"]
    
    assert "python" in report.matched_skills
    assert "Docker" in report.missing_skills


def test_final_ats_node_with_improperly_deserialized_model():
    """Verify final_ats_node re-validates models that have dictionary-typed nested fields due to LangGraph checkpoints."""
    
    # Create an outer model, but assign a raw dictionary to the nested field!
    resume_model = StructuredResume(skills=StructuredSkills())
    resume_model.skills = {
        "languages": ["Python", "Go"],
        "frameworks": ["FastAPI"],
        "tools": [],
        "databases": [],
        "concepts": []
    }
    resume_model.projects = [
        {"title": "Project A", "description": "Used Python and FastAPI to scale 10x", "tech_stack": []}
    ]
    
    jd_analysis = {
        "role_summary": "Role",
        "required_skills": ["Python"],
        "responsibilities": [],
        "keywords": [],
        "tools": [],
        "experience_requirements": ""
    }
    
    state = MagicMock()
    state.optimized_resume = resume_model
    state.jd_analysis = jd_analysis
    state.current_section = "DONE"
    
    # We should not crash on `resume.skills.languages` or `project.description` inside ats_engine
    with patch("app.services.ats_engine._get_embeddings", return_value=[[0.1]*384]):
        result = final_ats_node(state)
        
    assert "optimized_ats_report" in result
    report = result["optimized_ats_report"]
    assert "python" in report.matched_skills
    assert report.category_scores.quantified_impact > 0  # Should evaluate the project metric

    # No crash!
