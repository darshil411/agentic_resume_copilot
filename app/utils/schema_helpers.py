import logging
from typing import Any, Optional
from app.models.resume import StructuredResume, StructuredSkills, Project, Education
from app.models.jd import JDAnalysis

logger = logging.getLogger(__name__)

LIST_FIELDS = {
    "projects": Project,
    "education": Education,
}


def _coerce_list_field(value: Any, model_cls: Any, field_name: str) -> list:
    """Ensure a field that must be a list[ModelCls] is actually that.

    - If it is already a list, validate each item.
    - If it is a string (schema corruption from commit_changes_node), log a
      warning and return [] so validation can proceed.  The commit_changes_node
      fix prevents this from happening in normal operation; this is a last-resort
      safety net only.
    - If it is a dict, try to coerce it into ModelCls.
    """
    if value is None:
        return []
    if isinstance(value, str):
        logger.warning(
            "enforce_resume_schema: field '%s' was a string (schema corruption). "
            "Substituting empty list. Fix commit_changes_node if this persists.",
            field_name,
        )
        return []
    if isinstance(value, list):
        coerced = []
        for item in value:
            if isinstance(item, model_cls):
                coerced.append(item)
            elif isinstance(item, dict):
                try:
                    coerced.append(model_cls(**item))
                except Exception as exc:
                    logger.warning(
                        "enforce_resume_schema: skipped invalid %s entry: %s",
                        field_name, exc,
                    )
            else:
                logger.warning(
                    "enforce_resume_schema: skipped unexpected %s item type %s",
                    field_name, type(item),
                )
        return coerced
    # Unexpected scalar — log and return empty
    logger.warning(
        "enforce_resume_schema: field '%s' had unexpected type %s; substituting [].",
        field_name, type(value),
    )
    return []


def _coerce_skills(value: Any) -> StructuredSkills:
    if isinstance(value, StructuredSkills):
        return value
    if isinstance(value, dict):
        return StructuredSkills(**value)
    logger.warning(
        "enforce_resume_schema: skills field had unexpected type %s; using empty StructuredSkills.",
        type(value),
    )
    return StructuredSkills()


def enforce_resume_schema(resume_data: Any) -> Optional[StructuredResume]:
    """
    Safely reconstructs a StructuredResume from a dictionary or an improperly
    deserialized model crossing a checkpoint boundary.

    Validates every nested list field and coerces strings / dicts into proper
    model instances.  Logs a warning (rather than crashing) if a field has been
    corrupted; the ATS node can then score what it has.
    """
    if not resume_data:
        return None

    # Normalise to a plain dict so we can sanitise individual fields
    if isinstance(resume_data, StructuredResume):
        raw: dict = resume_data.__dict__.copy()
    elif isinstance(resume_data, dict):
        raw = dict(resume_data)
    else:
        return None

    # Sanitise nested list fields
    for field_name, model_cls in LIST_FIELDS.items():
        raw[field_name] = _coerce_list_field(raw.get(field_name), model_cls, field_name)

    # Sanitise skills
    raw["skills"] = _coerce_skills(raw.get("skills"))

    return StructuredResume(**raw)


def enforce_jd_schema(jd_data: Any) -> Optional[JDAnalysis]:
    """
    Safely reconstructs a JDAnalysis from a dictionary or an improperly 
    deserialized model crossing a checkpoint boundary.
    """
    if not jd_data:
        return None
    if isinstance(jd_data, dict):
        return JDAnalysis(**jd_data)
    elif isinstance(jd_data, JDAnalysis):
        return JDAnalysis(**jd_data.__dict__)
    return None

