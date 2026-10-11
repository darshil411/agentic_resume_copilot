from app.graph.nodes.foundation_nodes import _build_fallback_resume


def test_fallback_does_not_fabricate_credentials():
    raw = "John Doe\nSome random text mentioning Python and FastAPI and Postgres"
    fallback = _build_fallback_resume(raw)

    # Should not invent projects/experience/education/certifications
    assert fallback.projects == []
    assert fallback.experience == []
    assert fallback.education == []
    assert fallback.certifications == []
    # Should populate skills only if present in text
    assert "Python" in fallback.skills.languages
    assert (fallback.summary is not None)
