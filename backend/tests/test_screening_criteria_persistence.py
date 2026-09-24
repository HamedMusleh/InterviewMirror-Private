"""
Focused tests for the "Save Screening Criteria to DB" flow:

- ScreeningCriteriaRepository.save persists against the resolved
  JobOpportunity's integer id and follows the project's commit /
  refresh / rollback-on-failure transaction pattern.
- JobOpportunityRepository.get_by_job_id resolves a JobOpportunity by
  its string job_id.
- ScreeningCriteriaHandler wires generation + lookup + save together,
  and refuses to save (raising JobOpportunityNotFoundError) when no
  matching JobOpportunity exists.

These are unit tests against mocked SQLAlchemy Sessions, mirroring
the Mock-based style already used elsewhere in this test suite (see
tests/test_resume_parser.py), since the project has no test-database
fixture yet.
"""

from unittest.mock import MagicMock, Mock

import pytest

from app.database.models.job_opportunity import JobOpportunity
from app.handlers.screening_criteria_handler import (
    JobOpportunityNotFoundError,
    ScreeningCriteriaHandler,
)
from app.repositories.job_opportunity_repository import (
    JobOpportunityRepository,
)
from app.repositories.screening_criteria_repository import (
    ScreeningCriteriaRepository,
)
from app.schemas.screening_criteria import ScreeningCriteria


class _FakeLogger:
    def info(self, message: str) -> None:
        pass

    def warning(self, message: str) -> None:
        pass

    def error(self, message: str) -> None:
        pass


def _valid_screening_criteria() -> ScreeningCriteria:
    return ScreeningCriteria(
        **{
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
    )


# --------------------------------------------------------------------------
# ScreeningCriteriaRepository
# --------------------------------------------------------------------------


def test_screening_criteria_repository_save_uses_integer_job_opportunity_id():
    db = MagicMock()
    repository = ScreeningCriteriaRepository(db)
    criteria = _valid_screening_criteria()

    saved = repository.save(
        criteria,
        job_opportunity_id=42,
    )

    assert saved.job_id == 42

    # The string job_id must never leak into the FK column.
    assert saved.job_id != criteria.job_id

    assert saved.criteria["passing_score"] == 70

    assert (
        saved.criteria["screening_criteria"]["skills"]["weight"]
        == 40
    )

    assert "job_id" not in saved.criteria

    db.add.assert_called_once_with(saved)
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(saved)
    db.rollback.assert_not_called()


def test_screening_criteria_repository_save_rolls_back_on_failure():
    db = MagicMock()
    db.commit.side_effect = RuntimeError("db is down")

    repository = ScreeningCriteriaRepository(db)
    criteria = _valid_screening_criteria()

    with pytest.raises(RuntimeError):
        repository.save(
            criteria,
            job_opportunity_id=42,
        )

    db.rollback.assert_called_once()
    db.refresh.assert_not_called()


# --------------------------------------------------------------------------
# JobOpportunityRepository.get_by_job_id
# --------------------------------------------------------------------------


def test_job_opportunity_repository_get_by_job_id_found():
    expected_job = JobOpportunity(
        id=7,
        job_id="job-123",
    )

    db = MagicMock()

    (
        db.query.return_value
        .filter.return_value
        .first.return_value
    ) = expected_job

    repository = JobOpportunityRepository(db)

    result = repository.get_by_job_id("job-123")

    assert result is expected_job

    db.query.assert_called_once_with(JobOpportunity)


def test_job_opportunity_repository_get_by_job_id_not_found():
    db = MagicMock()

    (
        db.query.return_value
        .filter.return_value
        .first.return_value
    ) = None

    repository = JobOpportunityRepository(db)

    result = repository.get_by_job_id("does-not-exist")

    assert result is None


# --------------------------------------------------------------------------
# ScreeningCriteriaHandler
# --------------------------------------------------------------------------


def _make_handler(
    job_opportunity_repository,
    screening_criteria_repository,
):
    pipeline = Mock()

    return ScreeningCriteriaHandler(
        logger=_FakeLogger(),
        pipeline=pipeline,
        screening_criteria_repository=screening_criteria_repository,
        job_opportunity_repository=job_opportunity_repository,
    )


def test_handler_saves_criteria_when_job_opportunity_exists():
    criteria = _valid_screening_criteria()
    generated_pipeline_result = criteria

    job_opportunity_repository = Mock()

    job_opportunity_repository.get_by_job_id.return_value = (
        JobOpportunity(
            id=99,
            job_id="job-123",
        )
    )

    screening_criteria_repository = Mock()

    handler = _make_handler(
        job_opportunity_repository,
        screening_criteria_repository,
    )

    handler.pipeline.run.return_value = generated_pipeline_result

    result = handler.handle_generate_screening_criteria(
        {"any": "payload"}
    )

    job_opportunity_repository.get_by_job_id.assert_called_once_with(
        "job-123"
    )

    screening_criteria_repository.save.assert_called_once_with(
        generated_pipeline_result,
        99,
    )

    assert result is generated_pipeline_result


def test_handler_raises_when_job_opportunity_missing():
    criteria = _valid_screening_criteria()

    job_opportunity_repository = Mock()
    job_opportunity_repository.get_by_job_id.return_value = None

    screening_criteria_repository = Mock()

    handler = _make_handler(
        job_opportunity_repository,
        screening_criteria_repository,
    )

    handler.pipeline.run.return_value = criteria

    with pytest.raises(JobOpportunityNotFoundError):
        handler.handle_generate_screening_criteria(
            {"any": "payload"}
        )

    screening_criteria_repository.save.assert_not_called()