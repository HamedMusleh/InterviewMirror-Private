"""
Basic tests for the screening-criteria feature after the refactor.

These exercise the pieces that don't require a live Azure OpenAI
call: schema validation (including the new `extra="forbid"` rule)
and the skill-weight normalization logic used to post-process the
LLM's output.
"""

import pytest
from pydantic import ValidationError

from app.schemas.job_description import JobDescription
from app.schemas.screening_criteria import ScreeningCriteria
from app.services.screening_criteria_service import _normalize_skill_weights


class _FakeLogger:
    def info(self, message: str) -> None:
        pass

    def warning(self, message: str) -> None:
        pass

    def error(self, message: str) -> None:
        pass


def _valid_job_description_payload() -> dict:
    return {
        "role": {
            "title": "Backend Engineer",
            "department": "Engineering",
            "employment_type": "Full-time",
            "location": "Remote",
        },
        "job_summary": "Backend engineering role",
        "responsibilities": [
            "Build backend services",
        ],
        "requirements": {
            "skills": {
                "required": ["Python"],
                "preferred": ["FastAPI"],
            },
            "experience": {
                "minimum_years": 3,
                "level": "mid",
            },
        },
        "technical_stack": [
            "Python",
            "FastAPI",
        ],
        "soft_skills": [
            "Communication",
        ],
        "screening_settings": {
            "passing_score": 70,
        },
    }


def _valid_screening_criteria_payload() -> dict:
    return {
        "job_id": "job-123",
        "screening_criteria": {
            "skills": {
                "weight": 40,
                "required": [
                    {
                        "name": "Python",
                        "weight": 30,
                    }
                ],
                "preferred": [
                    {
                        "name": "FastAPI",
                        "weight": 10,
                    }
                ],
            },
            "experience": {
                "weight": 20,
                "minimum_years": 3,
                "level": "mid",
            },
            "education": {
                "weight": 10,
                "preferred_fields": [],
            },
            "projects": {
                "weight": 10,
                "required": False,
                "relevant_domains": [],
            },
            "certifications": {
                "weight": 10,
                "criteria": [],
            },
            "languages": {
                "weight": 5,
                "criteria": [],
            },
            "soft_skills": {
                "weight": 5,
                "criteria": [],
            },
        },
        "passing_score": 70,
    }


def test_job_description_parses_valid_payload():
    job_description = JobDescription(
        **_valid_job_description_payload()
    )

    assert job_description.role.title == "Backend Engineer"
    assert job_description.requirements.skills.required == ["Python"]


def test_screening_criteria_parses_valid_payload():
    criteria = ScreeningCriteria(
        **_valid_screening_criteria_payload()
    )

    assert criteria.job_id == "job-123"
    assert criteria.screening_criteria.skills.weight == 40


def test_screening_criteria_rejects_unknown_fields():
    """
    Nested ScreeningCriteria models must use extra="forbid" so the
    schema stays compatible with Azure OpenAI Structured Outputs.
    """
    payload = _valid_screening_criteria_payload()
    payload["screening_criteria"]["skills"]["unexpected_field"] = "nope"

    with pytest.raises(ValidationError):
        ScreeningCriteria(**payload)


def test_normalize_skill_weights_rescales_to_match_total():
    parsed = {
        "screening_criteria": {
            "skills": {
                "weight": 100,
                "required": [
                    {
                        "name": "Python",
                        "weight": 30,
                    }
                ],
                "preferred": [
                    {
                        "name": "FastAPI",
                        "weight": 30,
                    }
                ],
            }
        }
    }

    result = _normalize_skill_weights(
        parsed,
        _FakeLogger(),
    )

    skills = result["screening_criteria"]["skills"]

    total = sum(
        s["weight"]
        for s in skills["required"] + skills["preferred"]
    )

    assert total == skills["weight"]


def test_normalize_skill_weights_handles_rounding_remainder():
    """
    The rounded normalized weights must still sum exactly to total_weight.
    """
    parsed = {
        "screening_criteria": {
            "skills": {
                "weight": 10,
                "required": [
                    {
                        "name": "Python",
                        "weight": 1,
                    },
                    {
                        "name": "FastAPI",
                        "weight": 1,
                    },
                    {
                        "name": "SQL",
                        "weight": 1,
                    },
                ],
                "preferred": [],
            }
        }
    }

    result = _normalize_skill_weights(
        parsed,
        _FakeLogger(),
    )

    skills = result["screening_criteria"]["skills"]

    total = sum(
        s["weight"]
        for s in skills["required"] + skills["preferred"]
    )

    assert total == skills["weight"]


def test_normalize_skill_weights_no_skills_is_valid():
    """Case 1: no skills required -> valid by default, no error."""
    parsed = {
        "screening_criteria": {
            "skills": {
                "weight": 0,
                "required": [],
                "preferred": [],
            }
        }
    }

    result = _normalize_skill_weights(
        parsed,
        _FakeLogger(),
    )

    assert result == parsed


def test_normalize_skill_weights_all_zero_is_invalid():
    """
    Case 2: skills are required but their sum is 0 -> invalid,
    even if total_weight is also 0.
    """
    parsed = {
        "screening_criteria": {
            "skills": {
                "weight": 0,
                "required": [
                    {
                        "name": "Python",
                        "weight": 0,
                    }
                ],
                "preferred": [],
            }
        }
    }

    with pytest.raises(ValueError):
        _normalize_skill_weights(
            parsed,
            _FakeLogger(),
        )