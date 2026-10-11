import pytest
from app.utils.schema_helpers import _coerce_list_field, _coerce_skills
from app.models.resume import Project


def test_coerce_list_field_raises_on_unparseable_string():
    with pytest.raises(TypeError):
        _coerce_list_field("not-a-json-list", Project, "projects")


def test_coerce_skills_raises_on_unparseable_string():
    with pytest.raises(TypeError):
        _coerce_skills("languages: python")
